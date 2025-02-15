from flask import Flask, render_template, request, redirect, url_for, session, flash
import cx_Oracle
import sqlite3
import os
from functools import wraps

# Инициализация Oracle Instant Client (укажите корректный путь)
cx_Oracle.init_oracle_client(lib_dir="D:\\oracle\\instantclient_23_5")

app = Flask(__name__)
app.secret_key = 'замените_на_случайную_строку'  # для работы с сессиями

# Путь к SQLite БД
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB = os.path.join(BASE_DIR, 'users.db')


# Функция для получения подключения к SQLite
def get_db_connection():
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn


# Инициализация таблицы (если её ещё нет)
def init_sqlite_db():
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


# Инициализируем SQLite при старте приложения
init_sqlite_db()

# Список доступных баз данных с их параметрами
DB_CONFIGS = {
    'DB1': {'host': '192.168.0.113', 'port': 1521, 'service': 'prod'},
    'DB2': {'host': '192.168.0.116', 'port': 1521, 'service': 'stb'},
    'DB3': {'host': '192.168.0.115', 'port': 1521, 'service': 'ORCL3'},
}


# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Пожалуйста, авторизуйтесь для доступа к этой странице.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# Страница авторизации (логин ds, пароль oracle)
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'ds' and password == 'oracle':
            session['logged_in'] = True
            return redirect(url_for('select_db'))
        else:
            flash('Неверные учетные данные. Попробуйте ещё раз.', 'error')
    return render_template('login.html')


# Выход из системы (выход)
@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('login'))


# Страница выбора базы данных (доступна только после авторизации)
@app.route('/select-db', methods=['GET', 'POST'])
@login_required
def select_db():
    db_list = [{'name': key, **value} for key, value in DB_CONFIGS.items()]

    if request.method == 'POST':
        selected_db = request.form.get('db')
        if selected_db not in DB_CONFIGS:
            flash('Выберите корректную базу данных.', 'error')
            return redirect(url_for('select_db'))
        session['selected_db'] = selected_db
        return redirect(url_for('query'))

    return render_template('select_db.html', db_list=db_list)


# Страница с результатами запроса и обновлением данных (требуется авторизация)
@app.route('/query', methods=['GET', 'POST'])
@login_required
def query():
    selected_db = session.get('selected_db')
    if not selected_db or selected_db not in DB_CONFIGS:
        flash('Не выбрана база данных.', 'error')
        return redirect(url_for('select_db'))

    config = DB_CONFIGS[selected_db]
    dsn = cx_Oracle.makedsn(config['host'], config['port'], service_name=config['service'])

    # Подключаемся к Oracle и получаем пользователей
    oracle_users = []
    try:
        connection = cx_Oracle.connect(user='ds', password='oracle', dsn=dsn)
        cursor = connection.cursor()
        cursor.execute("SELECT username, ACCOUNT_STATUS FROM dba_users")
        oracle_users = cursor.fetchall()
    except Exception as e:
        flash(f'Ошибка подключения или выполнения запроса: {e}', 'error')
    finally:
        try:
            cursor.close()
            connection.close()
        except Exception:
            pass

    # Подключаемся к SQLite для синхронизации данных
    conn = get_db_connection()
    cur = conn.cursor()

    # Если форма отправлена, обновляем поля "номер заявки" и "описание"
    if request.method == 'POST':
        for key in request.form:
            if key.startswith('username_'):
                idx = key.split('_', 1)[1]
                username = request.form.get(f'username_{idx}')
                номер_заявки = request.form.get(f'номер_заявки_{idx}', '')
                описание = request.form.get(f'описание_{idx}', '')
                cur.execute('''
                    UPDATE oracle_users 
                    SET номер_заявки = ?, описание = ? 
                    WHERE db_name = ? AND username = ?
                ''', (номер_заявки, описание, selected_db, username))
        conn.commit()
        flash('Данные обновлены', 'success')

    # Собираем данные для таблицы
    table_data = []
    for row in oracle_users:
        username, account_status = row[0], row[1]
        cur.execute('''
            SELECT номер_заявки, описание FROM oracle_users 
            WHERE db_name = ? AND username = ?
        ''', (selected_db, username))
        record = cur.fetchone()
        if record is None:
            cur.execute('''
                INSERT INTO oracle_users (db_name, username, account_status, номер_заявки, описание)
                VALUES (?, ?, ?, '', '')
            ''', (selected_db, username, account_status))
            conn.commit()
            номер_заявки_val = ''
            описание_val = ''
        else:
            номер_заявки_val, описание_val = record['номер_заявки'], record['описание']
            cur.execute('''
                UPDATE oracle_users SET account_status = ?
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

    # Подсчитываем количество незаполненных записей
    incomplete_count = sum(1 for row in table_data if row['номер_заявки'] == '' or row['описание'] == '')

    # Сортировка: сначала незаполненные (подсвеченные красным)
    table_data.sort(key=lambda row: 0 if (row['номер_заявки'] == '' or row['описание'] == '') else 1)

    return render_template('query.html',
                           table_data=table_data,
                           selected_db=selected_db,
                           incomplete_count=incomplete_count)


if __name__ == '__main__':
    app.run(debug=True)
