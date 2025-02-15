import cx_Oracle
cx_Oracle.init_oracle_client(lib_dir="D:\oracle\instantclient_23_5")

DB_USER = 'ds'
DB_PASSWORD = 'oracle'

def get_users(db_host, db_service):
    dsn = f"{db_host}:1521/{db_service}"
    conn = cx_Oracle.connect(DB_USER, DB_PASSWORD, dsn)
    cursor = conn.cursor()
    cursor.execute("SELECT username, ACCOUNT_STATUS FROM dba_users")  # Замените на вашу таблицу
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users
