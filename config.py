# config.py

import os

# Список доступных баз данных
DB_CONFIGS = {
    'DB1': {'host': '192.168.0.113', 'port': 1521, 'service': 'prod'},
    'DB2': {'host': '192.168.0.116', 'port': 1521, 'service': 'stb'}

}

# Путь к SQLite
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB = os.path.join(BASE_DIR, 'users.db')

# Данные для Telegram
TELEGRAM_BOT_TOKEN = '7759968140:AAGR1CpKenY9v7m-FPpqYVHUQQi6MOhDxAI'
TELEGRAM_CHAT_ID = 'https://t.me/+tfCBpFIPbjNmNjBi'  # например, 123456789
#7759968140:AAGR1CpKenY9v7m-FPpqYVHUQQi6MOhDxAI