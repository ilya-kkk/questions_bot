#!/usr/bin/env python3
"""
Скрипт для применения миграций базы данных
"""
import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Параметры подключения к БД
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'database': os.getenv('POSTGRES_DB'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD'),
    'sslmode': 'disable'
}

# Таблица для отслеживания примененных миграций
MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW()
);
"""

def get_applied_migrations(conn):
    """Получает список примененных миграций"""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
        return {row[0] for row in cursor.fetchall()}
    finally:
        cursor.close()

def mark_migration_applied(conn, version):
    """Отмечает миграцию как примененную"""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO schema_migrations (version) VALUES (%s) ON CONFLICT (version) DO NOTHING",
            (version,)
        )
        conn.commit()
    finally:
        cursor.close()

def apply_migration(conn, migration_file):
    """Применяет одну миграцию"""
    version = migration_file.stem  # Имя файла без расширения
    
    print(f"Применение миграции: {migration_file.name}")
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        conn.commit()
        mark_migration_applied(conn, version)
        print(f"✓ Миграция {version} успешно применена")
    except Exception as e:
        conn.rollback()
        print(f"✗ Ошибка при применении миграции {version}: {e}")
        raise
    finally:
        cursor.close()

def main():
    """Основная функция для применения миграций"""
    # Проверяем наличие обязательных переменных
    if not DB_CONFIG['database']:
        print("Ошибка: POSTGRES_DB не установлен!")
        sys.exit(1)
    
    if not DB_CONFIG['user']:
        print("Ошибка: POSTGRES_USER не установлен!")
        sys.exit(1)
    
    # Путь к папке с миграциями
    migrations_dir = Path(__file__).parent / 'migrations'
    
    if not migrations_dir.exists():
        print(f"Ошибка: папка {migrations_dir} не найдена!")
        sys.exit(1)
    
    # Получаем список файлов миграций
    migration_files = sorted(migrations_dir.glob('*.sql'))
    
    if not migration_files:
        print("Миграции не найдены!")
        sys.exit(0)
    
    print(f"Найдено {len(migration_files)} миграций")
    print(f"Подключение к БД: host={DB_CONFIG['host']}, database={DB_CONFIG['database']}, user={DB_CONFIG['user']}")
    
    # Подключаемся к БД
    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except psycopg2.Error as e:
        print(f"Ошибка подключения к БД: {e}")
        sys.exit(1)
    
    try:
        # Создаем таблицу для отслеживания миграций
        cursor = conn.cursor()
        cursor.execute(MIGRATIONS_TABLE)
        conn.commit()
        cursor.close()
        
        # Получаем список примененных миграций
        applied_migrations = get_applied_migrations(conn)
        print(f"Уже применено миграций: {len(applied_migrations)}")
        
        # Применяем миграции по порядку
        applied_count = 0
        for migration_file in migration_files:
            version = migration_file.stem
            
            if version in applied_migrations:
                print(f"⊘ Миграция {version} уже применена, пропускаем")
                continue
            
            try:
                apply_migration(conn, migration_file)
                applied_count += 1
            except Exception as e:
                print(f"\nОстановка: ошибка при применении миграции {version}")
                print(f"Детали: {e}")
                sys.exit(1)
        
        if applied_count == 0:
            print("\nВсе миграции уже применены!")
        else:
            print(f"\n✓ Успешно применено {applied_count} новых миграций")
    
    finally:
        conn.close()
        print("Соединение с БД закрыто")

if __name__ == '__main__':
    main()

