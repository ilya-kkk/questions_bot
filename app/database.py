"""
Модуль для работы с базой данных
"""
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict
from app.config import DB_CONFIG
import random
import logging

logger = logging.getLogger(__name__)

class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self):
        self.config = DB_CONFIG
    
    def get_connection(self):
        """Создает и возвращает соединение с БД"""
        db_name = self.config.get('database')
        db_user = self.config.get('user')
        
        logger.debug(f"Подключение к БД: host={self.config.get('host')}, database={db_name}, user={db_user}")
        
        if not db_name:
            raise ValueError(f"ОШИБКА: database не установлен! config={self.config}")
        
        if db_name == db_user:
            raise ValueError(
                f"ОШИБКА: database совпадает с user! Это неправильно! "
                f"database={db_name}, user={db_user}. "
                f"Проверьте переменные окружения POSTGRES_DB и POSTGRES_USER"
            )
        
        connection_params = self.config.copy()
        logger.debug(f"Финальные параметры подключения: database={connection_params.get('database')}, user={connection_params.get('user')}")
        return psycopg2.connect(**connection_params)

    def get_random_question(self, user_id: int) -> Optional[Dict]:
        """Получает случайный вопрос, который еще не отмечен пользователем как выученный (оптимизированная версия)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Считаем количество невыученных вопросов для пользователя
                    cursor.execute(
                        """
                        SELECT COUNT(q.id)
                        FROM questions q
                        WHERE NOT EXISTS (
                            SELECT 1 FROM learned_questions l
                            WHERE l.question_id = q.id AND l.user_id = %s
                        )
                        """,
                        (user_id,)
                    )
                    unlearned_count = cursor.fetchone()['count']
                    
                    logger.info(f"Найдено {unlearned_count} невыученных вопросов для user_id={user_id}")

                    if unlearned_count == 0:
                        # Проверяем, есть ли вообще вопросы в базе
                        cursor.execute("SELECT COUNT(*) FROM questions")
                        if cursor.fetchone()['count'] > 0:
                            logger.info(f"Все вопросы выучены пользователем {user_id}")
                        else:
                            logger.info(f"В базе нет вопросов")
                        return None
                    
                    # Выбираем случайный offset
                    random_offset = random.randint(0, unlearned_count - 1)
                    
                    # Получаем случайный невыученный вопрос
                    cursor.execute(
                        """
                        SELECT q.id, q.question, q.topic, q.answer
                        FROM questions q
                        WHERE NOT EXISTS (
                            SELECT 1 FROM learned_questions l
                            WHERE l.question_id = q.id AND l.user_id = %s
                        )
                        ORDER BY q.id
                        LIMIT 1 OFFSET %s
                        """,
                        (user_id, random_offset)
                    )
                    
                    result = cursor.fetchone()
                    
                    if result:
                        logger.info(f"Найден вопрос: id={result['id']} (offset={random_offset})")
                        return result
                    else:
                        logger.warning(f"Неожиданно не найдено вопросов с offset={random_offset}, хотя unlearned_count={unlearned_count}")
                        return None

        except psycopg2.Error as e:
            logger.exception(f"Ошибка при получении случайного вопроса: {e}")
            return None
    
    def get_total_questions_count(self) -> int:
        """Возвращает общее количество вопросов в базе"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM questions")
                    return cursor.fetchone()[0]
        except psycopg2.Error as e:
            logger.exception(f"Ошибка при получении количества вопросов: {e}")
            return 0

    def get_learned_questions_count(self, user_id: int) -> int:
        """Возвращает количество вопросов, отмеченных пользователем как выученные"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT COUNT(*) FROM learned_questions WHERE user_id = %s",
                        (user_id,)
                    )
                    return cursor.fetchone()[0]
        except psycopg2.Error as e:
            logger.exception(f"Ошибка при получении количества выученных вопросов: {e}")
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
                    return result if result else None
        except psycopg2.Error as e:
            logger.exception(f"Ошибка при получении вопроса по id: {e}")
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
                    logger.info(f"Отмечен выученный вопрос: user_id={user_id}, question_id={question_id}, inserted={inserted}")
                    return inserted
        except psycopg2.Error as e:
            logger.exception(f"Ошибка при отметке вопроса как выученного: {e}")
            return False

    def log_user_action(self, username: str, question_id: int):
        """Логирует действие пользователя с вопросом в таблицу user_logs"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO user_logs (username, question_id)
                        VALUES (%s, %s)
                        """,
                        (username, question_id)
                    )
                    conn.commit()
                    logger.info(f"Записан лог: username={username}, question_id={question_id}")
        except psycopg2.Error as e:
            logger.exception(f"Ошибка при записи лога: {e}")
