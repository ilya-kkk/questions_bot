"""
Конфигурация телеграм бота
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен бота (получить у @BotFather)
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Параметры подключения к БД
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD'),
    'sslmode': 'disable'  # Отключаем SSL для подключения внутри Docker сети
}

# Валидация обязательных переменных окружения
required_vars = {
    'BOT_TOKEN': BOT_TOKEN,
    'POSTGRES_HOST': DB_CONFIG['host'],
    'POSTGRES_DB': DB_CONFIG['database'],
    'POSTGRES_USER': DB_CONFIG['user'],
    'POSTGRES_PASSWORD': DB_CONFIG['password']
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(
        f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}\n"
        f"Создайте файл .env на основе .env.example"
    )

# Настройки бота
BOT_SETTINGS = {
    'max_questions_per_user': 10,  # Максимальное количество вопросов на пользователя
    'timeout': 30  # Таймаут ожидания ответа в секундах
}

