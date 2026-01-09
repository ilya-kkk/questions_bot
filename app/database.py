"""
Модуль для работы с базой данных
"""
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict
from app.config import DB_CONFIG

# Настраиваем вывод print() в stdout с немедленным flush для docker logs
def print_flush(*args, **kwargs):
    """Обертка над print() с немедленным flush для docker logs"""
    print(*args, **kwargs, flush=True, file=sys.stdout)


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self):
        self.config = DB_CONFIG
    
    def get_connection(self):
        """Создает и возвращает соединение с БД"""
        db_name = self.config.get('database')
        db_user = self.config.get('user')
        
        print_flush(f"[DEBUG] Подключение к БД: host={self.config.get('host')}, database={db_name}, user={db_user}")
        
        if not db_name:
            raise ValueError(f"ОШИБКА: database не установлен! config={self.config}")
        
        if db_name == db_user:
            raise ValueError(
                f"ОШИБКА: database совпадает с user! Это неправильно! "
                f"database={db_name}, user={db_user}. "
                f"Проверьте переменные окружения POSTGRES_DB и POSTGRES_USER"
            )
        
        connection_params = self.config.copy()
        print_flush(f"[DEBUG] Финальные параметры подключения: database={connection_params.get('database')}, user={connection_params.get('user')}")
        return psycopg2.connect(**connection_params)

    def get_random_question(self, user_id: int) -> Optional[Dict]:
        """Получает случайный вопрос, который еще не отмечен пользователем как выученный"""
        try:
            with self.get_connection() as conn:
                # Используем обычный курсор для COUNT запросов
                with conn.cursor() as count_cursor:
                    # Сначала проверяем, есть ли вообще вопросы в базе
                    count_cursor.execute("SELECT COUNT(*) FROM questions")
                    total_questions = count_cursor.fetchone()[0]
                    print_flush(f"[DB] Всего вопросов в базе: {total_questions}")
                    
                    if total_questions == 0:
                        print_flush(f"[DB] В базе нет вопросов!")
                        return None
                    
                    # Проверяем, сколько вопросов выучено этим пользователем
                    count_cursor.execute(
                        "SELECT COUNT(*) FROM learned_questions WHERE user_id = %s",
                        (user_id,)
                    )
                    learned_count = count_cursor.fetchone()[0]
                    print_flush(f"[DB] Выучено вопросов пользователем {user_id}: {learned_count}")
                
                # Используем RealDictCursor для получения вопроса (чтобы вернуть словарь)
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Если пользователь не выучил ни одного вопроса, показываем любой случайный
                    if learned_count == 0:
                        print_flush(f"[DB] Пользователь не выучил ни одного вопроса, выбираем случайный из всех")
                        cursor.execute(
                            """
                            SELECT id, question, topic, answer
                            FROM questions
                            ORDER BY RANDOM()
                            LIMIT 1
                            """
                        )
                    else:
                        # Если есть выученные вопросы, выбираем из невыученных
                        print_flush(f"[DB] Выбираем из невыученных вопросов")
                        cursor.execute(
                            """
                            SELECT q.id, q.question, q.topic, q.answer
                            FROM questions q
                            WHERE NOT EXISTS (
                                SELECT 1 FROM learned_questions l
                                WHERE l.question_id = q.id AND l.user_id = %s
                            )
                            ORDER BY RANDOM()
                            LIMIT 1
                            """,
                            (user_id,)
                        )
                    
                    result = cursor.fetchone()
                    
                    if result:
                        print_flush(f"[DB] Найден вопрос: id={result['id']}")
                        return dict(result)
                    else:
                        # Если не нашли, значит все вопросы выучены
                        print_flush(f"[DB] Не найдено невыученных вопросов для user_id={user_id} (все {total_questions} вопросов выучены)")
                        return None
        except psycopg2.Error as e:
            import traceback
            error_details = traceback.format_exc()
            print_flush(f"[DB ERROR] Ошибка при получении случайного вопроса: {e}")
            print_flush(f"[DB ERROR] Детали: {error_details}")
            return None
    
    def get_total_questions_count(self) -> int:
        """Возвращает общее количество вопросов в базе"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM questions")
                    return cursor.fetchone()[0]
        except psycopg2.Error as e:
            print_flush(f"Ошибка при получении количества вопросов: {e}")
            return 0

    def get_question_by_id(self, question_id: int) -> Optional[Dict]:
        """Возвращает вопрос по id"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        "SELECT id, question, topic, answer FROM questions WHERE id = %s",
                        (question_id,)
                    )
                    result = cursor.fetchone()
                    return dict(result) if result else None
        except psycopg2.Error as e:
            print_flush(f"Ошибка при получении вопроса по id: {e}")
            return None

    def mark_question_learned(self, user_id: int, username: Optional[str], question_id: int) -> bool:
        """Отмечает вопрос как выученный для пользователя. Возвращает True, если добавили новую запись."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO learned_questions (user_id, username, question_id)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id, question_id) DO NOTHING
                        """,
                        (user_id, username, question_id)
                    )
                    inserted = cursor.rowcount > 0
                    conn.commit()
                    print_flush(f"[DB] Отмечен выученный вопрос: user_id={user_id}, question_id={question_id}, inserted={inserted}")
                    return inserted
        except psycopg2.Error as e:
            print_flush(f"Ошибка при отметке вопроса как выученного: {e}")
            return False

