#!/usr/bin/env python3
"""
Скрипт для импорта данных из raw.json в PostgreSQL базу данных
"""

import json
import psycopg2
from psycopg2.extras import execute_values
import sys
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла только если они не установлены
# В docker-compose переменные уже установлены, поэтому load_dotenv не нужен
# Но оставляем для локального запуска
if not os.getenv('DB_HOST') and not os.getenv('POSTGRES_HOST'):
    load_dotenv()

# Параметры подключения к БД из переменных окружения
# Используем те же переменные, что и в app/config.py для консистентности
# Приоритет: DB_* переменные (как в app/config.py), затем POSTGRES_* (для обратной совместимости)
def get_db_config():
    """Получает конфигурацию БД из переменных окружения"""
    host = os.getenv('DB_HOST')
    if not host:
        host = os.getenv('POSTGRES_HOST', 'localhost')
    
    port = os.getenv('DB_PORT')
    if not port:
        port = os.getenv('POSTGRES_PORT', '5432')
    
    database = os.getenv('DB_NAME')
    if not database:
        database = os.getenv('POSTGRES_DB', 'questions_db')
    
    user = os.getenv('DB_USER')
    if not user:
        user = os.getenv('POSTGRES_USER', 'postgres')
    
    password = os.getenv('DB_PASSWORD')
    if not password:
        password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    
    config = {
        'host': host,
        'port': int(port),
        'database': database,
        'user': user,
        'password': password,
        'sslmode': 'disable'  # Отключаем SSL для подключения внутри Docker сети
    }
    
    print(f"Подключение к БД: host={config['host']}, database={config['database']}, user={config['user']}")
    return config

def create_table(cursor):
    """Создает таблицу questions если её нет"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY,
            question TEXT NOT NULL,
            topic TEXT,
            answer TEXT
        )
    """)
    print("Таблица questions создана или уже существует")

def import_data(json_file='raw.json'):
    """Импортирует данные из JSON файла в БД"""
    
    # Читаем JSON файл
    if not os.path.exists(json_file):
        print(f"Ошибка: файл {json_file} не найден")
        sys.exit(1)
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Загружено {len(data)} записей из {json_file}")
    
    # Получаем конфигурацию БД
    DB_CONFIG = get_db_config()
    
    # Подключаемся к БД
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Создаем таблицу
        create_table(cursor)
        conn.commit()
        
        # Подготавливаем данные для вставки
        records = [(item['id'], item['question'], item.get('topic', ''), item.get('answer', '')) 
                   for item in data]
        
        # Вставляем данные (используем ON CONFLICT для обновления существующих записей)
        insert_query = """
            INSERT INTO questions (id, question, topic, answer)
            VALUES %s
            ON CONFLICT (id) 
            DO UPDATE SET 
                question = EXCLUDED.question,
                topic = EXCLUDED.topic,
                answer = EXCLUDED.answer
        """
        
        execute_values(cursor, insert_query, records)
        conn.commit()
        
        print(f"Успешно импортировано {len(records)} записей в базу данных")
        
        # Проверяем количество записей в БД
        cursor.execute("SELECT COUNT(*) FROM questions")
        count = cursor.fetchone()[0]
        print(f"Всего записей в таблице: {count}")
        
    except psycopg2.Error as e:
        print(f"Ошибка при работе с БД: {e}")
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("Соединение с БД закрыто")

if __name__ == '__main__':
    import_data()

