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
        db_name = self.config.get('database')
        db_user = self.config.get('user')
        
        print(f"[DEBUG] Подключение к БД: host={self.config.get('host')}, database={db_name}, user={db_user}")
        
        if not db_name:
            raise ValueError(f"ОШИБКА: database не установлен! config={self.config}")
        
        if db_name == db_user:
            raise ValueError(
                f"ОШИБКА: database совпадает с user! Это неправильно! "
                f"database={db_name}, user={db_user}. "
                f"Проверьте переменные окружения POSTGRES_DB и POSTGRES_USER"
            )
        
        # Убеждаемся, что используем правильный параметр для psycopg2
        # psycopg2 принимает и 'database' и 'dbname', но мы явно используем 'database'
        connection_params = self.config.copy()
        
        # Дополнительная проверка перед подключением
        print(f"[DEBUG] Финальные параметры подключения: database={connection_params.get('database')}, user={connection_params.get('user')}")
        
        return psycopg2.connect(**connection_params)   
    
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
                    # Проверяем и добавляем колонку user_answer, если её нет
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'logs' 
                        AND column_name = 'user_answer'
                    """)
                    if cursor.fetchone() is None:
                        cursor.execute("ALTER TABLE logs ADD COLUMN IF NOT EXISTS user_answer TEXT")
                        conn.commit()
                        print("Колонка user_answer добавлена в таблицу logs")
                elif not user_logs_exists:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS user_logs (
                            id SERIAL PRIMARY KEY,
                            timestamp TIMESTAMP DEFAULT NOW(),
                            username TEXT NOT NULL,
                            question_id INTEGER NOT NULL,
                            user_answer TEXT,
                            FOREIGN KEY (question_id) REFERENCES questions(id)
                        )
                    """)
                    conn.commit()
                    print("Таблица user_logs успешно создана/проверена")
                else:
                    print("Таблица user_logs уже существует")
                    # Проверяем и добавляем колонку user_answer, если её нет
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'user_logs' 
                        AND column_name = 'user_answer'
                    """)
                    if cursor.fetchone() is None:
                        cursor.execute("ALTER TABLE user_logs ADD COLUMN IF NOT EXISTS user_answer TEXT")
                        conn.commit()
                        print("Колонка user_answer добавлена в таблицу user_logs")
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
    
    def log_question_answer(self, username: str, question_id: int, user_answer: Optional[str] = None, timestamp: Optional[datetime] = None):
        """
        Записывает лог ответа пользователя на вопрос
        
        Args:
            username: Имя пользователя Telegram
            question_id: ID вопроса
            user_answer: Ответ пользователя (опционально)
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
                
                # Проверяем, есть ли колонка user_answer в таблице
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = %s 
                    AND column_name = 'user_answer'
                """, (table_name,))
                has_user_answer_column = cursor.fetchone() is not None
                
                # Если колонки нет, добавляем её (для существующих таблиц)
                if not has_user_answer_column:
                    try:
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS user_answer TEXT")
                        conn.commit()
                        has_user_answer_column = True  # Обновляем флаг после успешного добавления
                        print(f"Колонка user_answer добавлена в таблицу {table_name}")
                    except Exception as e:
                        print(f"Не удалось добавить колонку user_answer: {e}")
                        conn.rollback()
                
                # Вставляем данные с учетом наличия колонки user_answer
                if timestamp:
                    if has_user_answer_column:
                        cursor.execute(
                            f"""
                            INSERT INTO {table_name} (timestamp, username, question_id, user_answer)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (timestamp, username, question_id, user_answer)
                        )
                    else:
                        cursor.execute(
                            f"""
                            INSERT INTO {table_name} (timestamp, username, question_id)
                            VALUES (%s, %s, %s)
                            """,
                            (timestamp, username, question_id)
                        )
                else:
                    if has_user_answer_column:
                        cursor.execute(
                            f"""
                            INSERT INTO {table_name} (username, question_id, user_answer)
                            VALUES (%s, %s, %s)
                            """,
                            (username, question_id, user_answer)
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
                print(f"Лог успешно записан: username={username}, question_id={question_id}, user_answer={'сохранен' if user_answer else 'не указан'}")
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

