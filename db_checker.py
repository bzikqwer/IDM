# db_checker.py

import cx_Oracle
import sqlite3
import os
import config



def get_db_connection():
    """Подключение к локальной SQLite (users.db)."""
    conn = sqlite3.connect(config.SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn

def check_all_databases():
    """
    Подключается к каждой базе из config.DB_CONFIGS,
    проверяет доступность и подсчитывает количество
    незаполненных (номер_заявки или описание) записей
    в таблице oracle_users.

    Возвращает список словарей вида:
    [
      {
        "db_name": "DB1",
        "unavailable": False,
        "incomplete_count": 5
      },
      ...
    ]
    """
    results = []
    conn = get_db_connection()
    cur = conn.cursor()

    for db_name, db_params in config.DB_CONFIGS.items():
        dsn = cx_Oracle.makedsn(
            db_params['host'],
            db_params['port'],
            service_name=db_params['service']
        )

        unavailable = False
        incomplete_count = 0

        try:
            # Подключаемся к Oracle
            with cx_Oracle.connect('ds', 'oracle', dsn) as oracle_conn:
                with oracle_conn.cursor() as cursor:
                    cursor.execute("SELECT username, account_status FROM dba_users")
                    oracle_list = cursor.fetchall()

            # Синхронизируем с локальной таблицей oracle_users
            for (username, account_status) in oracle_list:
                cur.execute('''
                    SELECT номер_заявки, описание
                    FROM oracle_users
                    WHERE db_name = ? AND username = ?
                ''', (db_name, username))
                record = cur.fetchone()

                if record is None:
                    # Вставляем
                    cur.execute('''
                        INSERT INTO oracle_users (db_name, username, account_status, номер_заявки, описание)
                        VALUES (?, ?, ?, '', '')
                    ''', (db_name, username, account_status))
                    номер_заявки_val = ''
                    описание_val = ''
                else:
                    номер_заявки_val, описание_val = record['номер_заявки'], record['описание']
                    # Обновим account_status
                    cur.execute('''
                        UPDATE oracle_users
                        SET account_status = ?
                        WHERE db_name = ? AND username = ?
                    ''', (account_status, db_name, username))

                # Если поля пусты, увеличиваем счетчик
                if номер_заявки_val == '' or описание_val == '':
                    incomplete_count += 1

            conn.commit()

        except Exception:
            # Если упали в ошибку, считаем базу недоступной
            unavailable = True
            incomplete_count = 0

        results.append({
            "db_name": db_name,
            "unavailable": unavailable,
            "incomplete_count": incomplete_count
        })

    cur.close()
    conn.close()
    return results
