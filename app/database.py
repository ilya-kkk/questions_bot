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
        """Создает таблицу logs если её нет"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS logs (
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMP DEFAULT NOW(),
                            username TEXT NOT NULL,
                            question_id INTEGER NOT NULL,
                            FOREIGN KEY (question_id) REFERENCES questions(id)
                        )
                    """)
                    conn.commit()
        except psycopg2.Error as e:
            print(f"Ошибка при создании таблицы logs: {e}")
    
    def log_question_answer(self, username: str, question_id: int, timestamp: Optional[datetime] = None):
        """
        Записывает лог ответа пользователя на вопрос
        
        Args:
            username: Имя пользователя Telegram
            question_id: ID вопроса
            timestamp: Временная метка (если None, используется NOW())
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    if timestamp:
                        cursor.execute(
                            """
                            INSERT INTO logs (timestamp, username, question_id)
                            VALUES (%s, %s, %s)
                            """,
                            (timestamp, username, question_id)
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO logs (username, question_id)
                            VALUES (%s, %s)
                            """,
                            (username, question_id)
                        )
                    conn.commit()
        except psycopg2.Error as e:
            print(f"Ошибка при записи лога: {e}")

