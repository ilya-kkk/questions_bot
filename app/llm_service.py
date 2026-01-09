"""
Модуль для работы с OpenAI/OpenRouter API для оценки ответов пользователей
"""
import os
import logging
import openai
import httpx
from typing import Optional
from app.config import LLM_API_KEY, LLM_PROXY_URL, LLM_TIMEOUT

logger = logging.getLogger(__name__)


class UnsupportedRegionError(Exception):
    """Исключение для случая, когда OpenAI API недоступен в регионе"""
    pass


class LLMTimeoutError(Exception):
    """Исключение для случая таймаута при запросе к API"""
    pass


class LLMService:
    """Класс для работы с OpenAI/OpenRouter API"""
    
    def __init__(self):
        if not LLM_API_KEY:
            raise ValueError("LLM_API_KEY не установлен в переменных окружения")
        
        # Настраиваем клиент с прокси, если указан
        # Проверяем, используется ли OpenRouter (ключ начинается с sk-or-v1-)
        is_openrouter = LLM_API_KEY.startswith('sk-or-v1-') if LLM_API_KEY else False
        
        if is_openrouter:
            # Используем OpenRouter API
            base_url = "https://openrouter.ai/api/v1"
            client_kwargs = {
                'api_key': LLM_API_KEY,
                'base_url': base_url,
                'default_headers': {
                    'HTTP-Referer': 'https://github.com/your-repo',  # Опционально, для отслеживания
                    'X-Title': 'Questions Bot'  # Опционально, для идентификации
                }
            }
        else:
            # Используем стандартный OpenAI API
            client_kwargs = {'api_key': LLM_API_KEY}
        
        # Определяем прокси: сначала из LLM_PROXY_URL, потом из системных переменных
        proxy_url = LLM_PROXY_URL
        if not proxy_url:
            # Проверяем системные переменные окружения (если VLESS работает на уровне системы)
            proxy_url = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY') or os.getenv('https_proxy') or os.getenv('http_proxy')
        
        # Создаем HTTP клиент с увеличенным таймаутом
        # Используем более длинный таймаут для надежности, особенно при использовании прокси
        # Увеличиваем таймаут подключения, так как прокси может задерживать соединение
        http_timeout = httpx.Timeout(
            connect=30.0,  # Таймаут подключения (увеличен для прокси)
            read=LLM_TIMEOUT,  # Таймаут чтения ответа
            write=30.0,  # Таймаут записи (увеличен для прокси)
            pool=30.0  # Таймаут получения соединения из пула (увеличен для прокси)
        )
        
        if proxy_url:
            api_name = "OpenRouter API" if is_openrouter else "OpenAI API"
            print(f"Используется прокси для {api_name}: {proxy_url}")
            # Создаем HTTP клиент с прокси и увеличенным таймаутом
            http_client = httpx.Client(
                proxies=proxy_url,
                timeout=http_timeout,
                follow_redirects=True  # Следовать редиректам
            )
            client_kwargs['http_client'] = http_client
        else:
            api_name = "OpenRouter API" if is_openrouter else "OpenAI API"
            print(f"Прокси не настроен. Запросы идут напрямую к {api_name}.")
            # Создаем HTTP клиент без прокси, но с таймаутом
            http_client = httpx.Client(
                timeout=http_timeout,
                follow_redirects=True  # Следовать редиректам
            )
            client_kwargs['http_client'] = http_client
        
        # Отключаем повторные попытки, чтобы избежать увеличения времени ожидания
        # max_retries=0 означает, что при ошибке запрос не будет повторяться
        client_kwargs['max_retries'] = 0
        
        self.client = openai.OpenAI(**client_kwargs)
        
        # Проверяем фактический таймаут HTTP клиента
        if hasattr(self.client, '_client') and hasattr(self.client._client, '_client'):
            actual_timeout = getattr(self.client._client._client, 'timeout', None)
            if actual_timeout:
                logger.info(f"Фактический таймаут HTTP клиента: {actual_timeout}")
            else:
                logger.warning("Не удалось определить фактический таймаут HTTP клиента")
        
        logger.info(f"OpenAI клиент инициализирован. Настроенный таймаут: connect=30.0s, read={LLM_TIMEOUT}s, write=30.0s, pool=30.0s")
    
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
        
        # Логируем начало запроса
        import time
        start_time = time.time()
        logger.info(f"Начало запроса к LLM API (таймаут: {LLM_TIMEOUT} сек)")
        
        try:
            # Таймаут контролируется через http_client, настроенный в __init__
            # Не используем параметр timeout в create(), так как он может не поддерживаться
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=200  # Ограничиваем длину ответа для короткого совета
            )
            
            elapsed_time = time.time() - start_time
            logger.info(f"Запрос к LLM API выполнен успешно за {elapsed_time:.2f} секунд")
            
            if not response.choices or not response.choices[0].message:
                raise ValueError("Пустой ответ от OpenAI API")
            
            return response.choices[0].message.content.strip()
        
        except (httpx.TimeoutException, TimeoutError) as e:
            # Обработка ошибок таймаута
            import traceback
            elapsed_time = time.time() - start_time
            error_details = traceback.format_exc()
            logger.error(
                f"Таймаут при запросе к LLM API. "
                f"Прошло времени: {elapsed_time:.2f} секунд, "
                f"Таймаут: {LLM_TIMEOUT} секунд, "
                f"Ошибка: {str(e)}, "
                f"Тип ошибки: {type(e).__name__}\n"
                f"Детали ошибки:\n{error_details}"
            )
            raise LLMTimeoutError(
                f"Запрос к LLM API превысил таймаут ({LLM_TIMEOUT} секунд). "
                f"Фактическое время ожидания: {elapsed_time:.2f} секунд. "
                f"Возможные причины: медленное соединение, проблемы с прокси, перегрузка API. "
                f"Попробуйте позже или проверьте настройки прокси."
            )
        except openai.APIError as e:
            # Обработка ошибки 403 - регион не поддерживается
            elapsed_time = time.time() - start_time
            error_str = str(e)
            error_msg_lower = error_str.lower()
            
            # Проверяем различные способы определения ошибки региона
            if ('403' in error_str or 
                'unsupported_country' in error_msg_lower or 
                'unsupported_country_region_territory' in error_msg_lower or
                'country, region, or territory not supported' in error_msg_lower):
                import traceback
                error_details = traceback.format_exc()
                logger.error(
                    f"OpenAI API недоступен в регионе (APIError). "
                    f"Ошибка: {error_str}, "
                    f"Тип ошибки: {type(e).__name__}\n"
                    f"Детали ошибки:\n{error_details}"
                )
                raise UnsupportedRegionError(
                    "OpenAI API недоступен в вашем регионе. "
                    "Используйте VPN или альтернативный LLM API (Yandex GPT, Anthropic Claude и т.д.)"
                )
            # Логируем другие ошибки API
            import traceback
            error_details = traceback.format_exc()
            logger.error(
                f"Ошибка OpenAI API (не связанная с регионом). "
                f"Ошибка: {error_str}, "
                f"Тип ошибки: {type(e).__name__}\n"
                f"Детали ошибки:\n{error_details}"
            )
            raise  # Пробрасываем другие ошибки API
        except Exception as e:
            # Обрабатываем другие типы ошибок (например, из response)
            elapsed_time = time.time() - start_time
            error_str = str(e)
            if 'unsupported_country' in error_str.lower() or '403' in error_str:
                import traceback
                error_details = traceback.format_exc()
                logger.error(
                    f"OpenAI API недоступен в регионе (общая ошибка). "
                    f"Ошибка: {error_str}, "
                    f"Тип ошибки: {type(e).__name__}\n"
                    f"Детали ошибки:\n{error_details}"
                )
                raise UnsupportedRegionError(
                    "OpenAI API недоступен в вашем регионе. "
                    "Используйте VPN или альтернативный LLM API (Yandex GPT, Anthropic Claude и т.д.)"
                )
            # Логируем другие ошибки
            import traceback
            error_details = traceback.format_exc()
            logger.error(
                f"Неожиданная ошибка при вызове OpenAI API. "
                f"Ошибка: {error_str}, "
                f"Тип ошибки: {type(e).__name__}\n"
                f"Детали ошибки:\n{error_details}"
            )
            raise

