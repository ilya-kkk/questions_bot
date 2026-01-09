"""
Конфигурация телеграм бота
"""
import os
import sys
from dotenv import load_dotenv

# Функция для немедленного вывода в docker logs
def print_flush(*args, **kwargs):
    """Обертка над print() с немедленным flush для docker logs"""
    print(*args, **kwargs, flush=True, file=sys.stdout)

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен бота (получить у @BotFather)
BOT_TOKEN = os.getenv('BOT_TOKEN')

# API ключ для OpenAI/OpenRouter (для оценки ответов)
# OpenRouter ключи начинаются с sk-or-v1-, OpenAI ключи начинаются с sk-
LLM_API_KEY = os.getenv('LLM_API_KEY')

# Прокси для OpenAI API (опционально)
# Если VLESS клиент работает на сервере, используйте локальный HTTP прокси
# Обычно v2ray/xray создает HTTP прокси на localhost:10808 или другом порту
# Если VLESS работает на уровне системы, оставьте пустым и используйте системные переменные HTTP_PROXY/HTTPS_PROXY
LLM_PROXY_URL = os.getenv('LLM_PROXY_URL', '')

# Параметры подключения к БД
# ВАЖНО: Используем POSTGRES_DB для имени базы данных, а не POSTGRES_USER!
postgres_db = os.getenv('POSTGRES_DB')
postgres_user = os.getenv('POSTGRES_USER')

# Проверяем, что POSTGRES_DB установлен и не равен POSTGRES_USER
if not postgres_db:
    raise ValueError(
        "КРИТИЧЕСКАЯ ОШИБКА: POSTGRES_DB не установлен! "
        "Проверьте файл .env и убедитесь, что POSTGRES_DB=app_db"
    )

if postgres_db == postgres_user:
    raise ValueError(
        f"КРИТИЧЕСКАЯ ОШИБКА: POSTGRES_DB совпадает с POSTGRES_USER! "
        f"POSTGRES_DB={postgres_db}, POSTGRES_USER={postgres_user}. "
        f"Это неправильно! POSTGRES_DB должно быть именем базы данных (app_db), "
        f"а POSTGRES_USER - именем пользователя (app_user)"
    )

DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'database': postgres_db,  # Явно используем переменную, чтобы избежать путаницы
    'user': postgres_user,
    'password': os.getenv('POSTGRES_PASSWORD'),
    'sslmode': 'disable'  # Отключаем SSL для подключения внутри Docker сети
}

# Дополнительная проверка после создания конфига
print_flush(f"[CONFIG] DB_CONFIG создан: host={DB_CONFIG['host']}, database={DB_CONFIG['database']}, user={DB_CONFIG['user']}")


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

# Настройки LLM API
LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', '90'))  # Таймаут для запросов к LLM API в секундах (по умолчанию 90)

