"""
Модуль для работы с OpenAI API для оценки ответов пользователей
"""
import openai
import httpx
from typing import Optional
from app.config import LLM_API_KEY, LLM_PROXY_URL


class UnsupportedRegionError(Exception):
    """Исключение для случая, когда OpenAI API недоступен в регионе"""
    pass


class LLMService:
    """Класс для работы с OpenAI API"""
    
    def __init__(self):
        if not LLM_API_KEY:
            raise ValueError("LLM_API_KEY не установлен в переменных окружения")
        
        # Настраиваем клиент с прокси, если указан
        client_kwargs = {'api_key': LLM_API_KEY}
        
        if LLM_PROXY_URL:
            print(f"Используется прокси для OpenAI API: {LLM_PROXY_URL}")
            # Создаем HTTP клиент с прокси
            client_kwargs['http_client'] = httpx.Client(
                proxies=LLM_PROXY_URL,
                timeout=30.0
            )
        
        self.client = openai.OpenAI(**client_kwargs)
    
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
        
        try:
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
        
        except openai.APIError as e:
            # Обработка ошибки 403 - регион не поддерживается
            error_str = str(e)
            error_msg_lower = error_str.lower()
            
            # Проверяем различные способы определения ошибки региона
            if ('403' in error_str or 
                'unsupported_country' in error_msg_lower or 
                'unsupported_country_region_territory' in error_msg_lower or
                'country, region, or territory not supported' in error_msg_lower):
                raise UnsupportedRegionError(
                    "OpenAI API недоступен в вашем регионе. "
                    "Используйте VPN или альтернативный LLM API (Yandex GPT, Anthropic Claude и т.д.)"
                )
            raise  # Пробрасываем другие ошибки API
        except Exception as e:
            # Обрабатываем другие типы ошибок (например, из response)
            error_str = str(e)
            if 'unsupported_country' in error_str.lower() or '403' in error_str:
                raise UnsupportedRegionError(
                    "OpenAI API недоступен в вашем регионе. "
                    "Используйте VPN или альтернативный LLM API (Yandex GPT, Anthropic Claude и т.д.)"
                )
            raise

