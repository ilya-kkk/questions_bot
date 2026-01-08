"""
Модуль для работы с базой данных
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict
from datetime import datetime
from app.config import DB_CONFIG


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self):
        self.config = DB_CONFIG
    
    def get_connection(self):
        """Создает и возвращает соединение с БД"""
        # Отладочный вывод для проверки конфигурации
        print(f"[DEBUG] Подключение к БД: host={self.config.get('host')}, database={self.config.get('database')}, user={self.config.get('user')}")
        if not self.config.get('database'):
            raise ValueError(f"ОШИБКА: database не установлен! config={self.config}")
        if self.config.get('database') == self.config.get('user'):
            raise ValueError(f"ОШИБКА: database совпадает с user! Это неправильно! database={self.config.get('database')}, user={self.config.get('user')}")
        return psycopg2.connect(**self.config)   
    
    def get_random_question(self) -> Optional[Dict]:
        """Получает случайный вопрос"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT id, question, topic, answer 
                        FROM questions 
                        ORDER BY RANDOM() 
                        LIMIT 1
                        """
                    )
                    result = cursor.fetchone()
                    return dict(result) if result else None
        except psycopg2.Error as e:
            print(f"Ошибка при получении случайного вопроса: {e}")
            return None
    
    def create_logs_table(self):
        """Создает таблицу user_logs если её нет (или использует существующую таблицу logs)"""
        try:
            conn = self.get_connection()
            try:
                cursor = conn.cursor()
                # Проверяем, существует ли таблица logs
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'logs'
                    )
                """)
                logs_exists = cursor.fetchone()[0]
                
                # Проверяем, существует ли таблица user_logs
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'user_logs'
                    )
                """)
                user_logs_exists = cursor.fetchone()[0]
                
                # Если существует таблица logs, используем её, иначе создаем user_logs
                if logs_exists:
                    print("Таблица logs уже существует, используем её")
                elif not user_logs_exists:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS user_logs (
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMP DEFAULT NOW(),
                            username TEXT NOT NULL,
                            question_id INTEGER NOT NULL,
                            FOREIGN KEY (question_id) REFERENCES questions(id)
                        )
                    """)
                    conn.commit()
                    print("Таблица user_logs успешно создана/проверена")
                else:
                    print("Таблица user_logs уже существует")
            except Exception as e:
                conn.rollback()
                raise
            finally:
                conn.close()
        except psycopg2.Error as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Ошибка при создании таблицы user_logs: {e}")
            print(f"Детали ошибки: {error_details}")
    
    def log_question_answer(self, username: str, question_id: int, timestamp: Optional[datetime] = None):
        """
        Записывает лог ответа пользователя на вопрос
        
        Args:
            username: Имя пользователя Telegram
            question_id: ID вопроса
            timestamp: Временная метка (если None, используется NOW())
        """
        try:
            conn = self.get_connection()
            try:
                cursor = conn.cursor()
                # Проверяем, какая таблица существует: logs или user_logs
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'logs'
                    )
                """)
                logs_exists = cursor.fetchone()[0]
                
                table_name = 'logs' if logs_exists else 'user_logs'
                
                if timestamp:
                    cursor.execute(
                        f"""
                        INSERT INTO {table_name} (timestamp, username, question_id)
                        VALUES (%s, %s, %s)
                        """,
                        (timestamp, username, question_id)
                    )
                else:
                    cursor.execute(
                        f"""
                        INSERT INTO {table_name} (username, question_id)
                        VALUES (%s, %s)
                        """,
                        (username, question_id)
                    )
                conn.commit()
                cursor.close()
                print(f"Лог успешно записан: username={username}, question_id={question_id}")
            except Exception as e:
                conn.rollback()
                raise
            finally:
                conn.close()
        except psycopg2.Error as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Ошибка при записи лога: {e}")
            print(f"Детали ошибки: {error_details}")
            raise  # Пробрасываем исключение для обработки выше

