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

# Загружаем переменные окружения из .env файла
load_dotenv()

# Параметры подключения к БД из переменных окружения
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'database': os.getenv('POSTGRES_DB'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD')
}

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

