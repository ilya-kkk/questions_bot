"""
Модуль для работы с OpenAI API для оценки ответов пользователей
"""
import openai
from typing import Optional
from app.config import LLM_API_KEY


class LLMService:
    """Класс для работы с OpenAI API"""
    
    def __init__(self):
        if not LLM_API_KEY:
            raise ValueError("LLM_API_KEY не установлен в переменных окружения")
        self.client = openai.OpenAI(api_key=LLM_API_KEY)
    
    def evaluate_answer(self, question: str, user_answer: str, correct_answer: Optional[str] = None) -> str:
        """
        Оценивает ответ пользователя и возвращает совет по улучшению
        
        Args:
            question: Текст вопроса
            user_answer: Ответ пользователя
            correct_answer: Правильный ответ (опционально, для справки)
        
        Returns:
            str: Оценка и короткий совет по улучшению ответа
        """
        # Формируем системный промпт
        system_prompt = (
            "Ты эксперт по техническим собеседованиям по машинному обучению. "
            "Оцени ответ пользователя на вопрос и дай короткий (2-3 предложения) совет по улучшению ответа."
        )
        
        # Формируем промпт с вопросом и ответами
        user_prompt = f"Вопрос: {question}\n\n"
        if correct_answer:
            user_prompt += f"Правильный ответ (для справки): {correct_answer}\n\n"
        user_prompt += f"Ответ пользователя: {user_answer}\n\n"
        user_prompt += "Дай оценку и короткий совет как улучшить мои знания и чего не хватает в моем ответе на вопрос."
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=200  # Ограничиваем длину ответа для короткого совета
        )
        
        if not response.choices or not response.choices[0].message:
            raise ValueError("Пустой ответ от OpenAI API")
        
        return response.choices[0].message.content.strip()

