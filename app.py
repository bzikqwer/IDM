# app.py

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import cx_Oracle
import sqlite3
import os
from functools import wraps
import config

# Импортируем функцию из нашего нового модуля:
from db_checker import check_all_databases

# Инициализация клиентской библиотеки Oracle
cx_Oracle.init_oracle_client(lib_dir="D:\\oracle\\instantclient_23_5")

app = Flask(__name__)
app.secret_key = 'замените_на_случайную_строку'  # для хранения сессий

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB = os.path.join(BASE_DIR, 'users.db')

def get_db_connection():
    """Подключение к локальной базе SQLite."""
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_sqlite_db():
    """Создание таблицы oracle_users, если её ещё нет."""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS oracle_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            db_name TEXT,
            username TEXT,
            account_status TEXT,
            номер_заявки TEXT,
            описание TEXT,
            UNIQUE(db_name, username)
        )
    ''')
    conn.commit()
    conn.close()

init_sqlite_db()

DB_CONFIGS = config.DB_CONFIGS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Пожалуйста, авторизуйтесь для доступа к этой странице.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Демонстрационные учетные данные
        if username == 'ds' and password == 'oracle':
            session['logged_in'] = True
            return redirect(url_for('select_db'))
        else:
            flash('Неверные учетные данные. Попробуйте ещё раз.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('login'))

@app.route('/select-db', methods=['GET', 'POST'])
@login_required
def select_db():
    """
    Отображаем страницу выбора базы.
    Быстрая загрузка: мы не проверяем каждую базу прямо сейчас,
    а лишь рендерим форму выбора. Асинхронная проверка будет
    сделана JavaScript'ом через /api/check-dbs.
    """
    db_list = [{'name': key, **value} for key, value in DB_CONFIGS.items()]

    if request.method == 'POST':
        selected_db = request.form.get('db')
        if selected_db not in DB_CONFIGS:
            flash('Выберите корректную базу данных.', 'error')
            return redirect(url_for('select_db'))
        session['selected_db'] = selected_db
        return redirect(url_for('query'))

    return render_template('select_db.html', db_list=db_list)

@app.route('/api/check-dbs', methods=['GET'])
@login_required
def api_check_dbs():
    """
    Новый эндпоинт, который вызывает вынесенную функцию check_all_databases()
    и возвращает результаты в формате JSON.
    """
    results = check_all_databases()
    return jsonify(results)

@app.route('/query', methods=['GET', 'POST'])
@login_required
def query():
    selected_db = session.get('selected_db')
    if not selected_db or selected_db not in DB_CONFIGS:
        flash('Не выбрана база данных.', 'error')
        return redirect(url_for('select_db'))

    db_params = DB_CONFIGS[selected_db]
    dsn = cx_Oracle.makedsn(db_params['host'], db_params['port'], service_name=db_params['service'])

    # Пытаемся прочитать пользователей из Oracle
    oracle_users = []
    try:
        connection = cx_Oracle.connect('ds', 'oracle', dsn)
        cursor = connection.cursor()
        cursor.execute("SELECT username, account_status FROM dba_users")
        oracle_users = cursor.fetchall()
    except Exception as e:
        flash(f'Ошибка подключения или выполнения запроса: {e}', 'error')
    finally:
        try:
            cursor.close()
            connection.close()
        except:
            pass

    # Синхронизируем с локальной БД
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        # Обновляем поля (номер_заявки, описание)
        for key in request.form:
            if key.startswith('username_'):
                idx = key.split('_', 1)[1]
                username = request.form.get(f'username_{idx}')
                номер_заявки_val = request.form.get(f'номер_заявки_{idx}', '')
                описание_val = request.form.get(f'описание_{idx}', '')
                cur.execute('''
                    UPDATE oracle_users 
                    SET номер_заявки = ?, описание = ?
                    WHERE db_name = ? AND username = ?
                ''', (номер_заявки_val, описание_val, selected_db, username))
        conn.commit()
        flash('Данные обновлены', 'success')

    # Собираем данные для вывода
    table_data = []
    for (username, account_status) in oracle_users:
        cur.execute('''
            SELECT номер_заявки, описание
            FROM oracle_users
            WHERE db_name = ? AND username = ?
        ''', (selected_db, username))
        record = cur.fetchone()

        if record is None:
            # Вставляем запись
            cur.execute('''
                INSERT INTO oracle_users (db_name, username, account_status, номер_заявки, описание)
                VALUES (?, ?, ?, '', '')
            ''', (selected_db, username, account_status))
            conn.commit()
            номер_заявки_val = ''
            описание_val = ''
        else:
            номер_заявки_val, описание_val = record['номер_заявки'], record['описание']
            # Обновим account_status
            cur.execute('''
                UPDATE oracle_users
                SET account_status = ?
                WHERE db_name = ? AND username = ?
            ''', (account_status, selected_db, username))
            conn.commit()

        table_data.append({
            'username': username,
            'account_status': account_status,
            'номер_заявки': номер_заявки_val,
            'описание': описание_val
        })

    conn.close()

    # Подсчитываем незаполненные
    incomplete_count = sum(1 for row in table_data if not row['номер_заявки'] or not row['описание'])
    # Чтобы незаполненные шли первыми, сортируем
    table_data.sort(key=lambda row: 0 if (row['номер_заявки'] == '' or row['описание'] == '') else 1)

    return render_template(
        'query.html',
        selected_db=selected_db,
        table_data=table_data,
        incomplete_count=incomplete_count
    )

if __name__ == '__main__':
    app.run(debug=True)
