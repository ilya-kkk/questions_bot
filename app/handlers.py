"""
Обработчики команд и сообщений для телеграм бота
"""
import asyncio
import logging
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.error import TimedOut as TelegramTimedOut
from telegram.ext import ContextTypes
from app.database import Database
from app.llm_service import LLMService, UnsupportedRegionError, LLMTimeoutError

logger = logging.getLogger(__name__)

# Настраиваем вывод логов в stdout для docker logs
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Функция для немедленного вывода в docker logs
def print_flush(*args, **kwargs):
    """Обертка над print() с немедленным flush для docker logs"""
    print(*args, **kwargs, flush=True, file=sys.stdout)

db = Database()

# Инициализируем LLM сервис (может быть None если ключ не установлен)
try:
    llm_service = LLMService()
except ValueError:
    llm_service = None
    print_flush("Предупреждение: LLM_API_KEY не установлен, оценка ответов будет недоступна")

# Создаем Reply Keyboard (кнопки рядом с полем ввода)
reply_keyboard = [
    [KeyboardButton("🎲 Случайный вопрос")]
]
reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        welcome_message = (
            "👋 Привет вкатун! Я бот чтобы ты наконецто заботал все вопросы и прошел собес на 300к наносек.\n\n"
        )
        try:
            await update.message.reply_text(welcome_message, reply_markup=reply_markup)
        except TelegramTimedOut as timeout_error:
            print_flush(f"[HANDLER ERROR] Таймаут при отправке приветственного сообщения: {timeout_error}")
            logger.error(f"Таймаут при отправке приветственного сообщения: {timeout_error}")
        except Exception as send_error:
            print_flush(f"[HANDLER ERROR] Ошибка при отправке приветственного сообщения: {send_error}")
            logger.error(f"Ошибка при отправке приветственного сообщения: {send_error}")
    except Exception as e:
        print_flush(f"[HANDLER ERROR] Ошибка в start handler: {e}")
        logger.error(f"Ошибка в start handler: {e}")
        if update and update.message:
            try:
                await update.message.reply_text("❌ Произошла ошибка при обработке команды", reply_markup=reply_markup)
            except Exception as error_send_error:
                print_flush(f"[HANDLER ERROR] Не удалось отправить сообщение об ошибке: {error_send_error}")
                logger.error(f"Не удалось отправить сообщение об ошибке: {error_send_error}")

async def random_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия на inline кнопку 'Случайный вопрос'"""
    query = update.callback_query
    await query.answer()
    
    question = db.get_random_question()
    
    if not question:
        await query.edit_message_text("❌ Не удалось получить вопрос из базы данных")
        return
    
    # Сохраняем вопрос в context для последующей обработки ответа
    context.user_data['current_question'] = {
        'id': question['id'],
        'question': question['question'],
        'topic': question.get('topic', ''),
        'answer': question.get('answer', '')
    }
    
    message = f"❓ <b>Вопрос #{question['id']}</b>\n\n"
    message += f"<b>Тема:</b> {question.get('topic', 'Не указана')}\n\n"
    message += f"<b>Вопрос:</b>\n{question['question']}\n\n"
    message += "💬 <b>Отправь свой ответ текстом, и я оценю его!</b>"
    
    # Создаем кнопку для обновления сообщения
    keyboard = [[InlineKeyboardButton("🎲 Случайный вопрос", callback_data="random_question")]]
    inline_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=inline_markup)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений (для Reply Keyboard кнопок)"""
    text = update.message.text
    
    # Обработка кнопки "Случайный вопрос" (приоритет над обработкой ответа)
    if text == "🎲 Случайный вопрос":
        # Очищаем предыдущий вопрос из контекста, если был
        if 'current_question' in context.user_data:
            del context.user_data['current_question']
        
        question = db.get_random_question()
        
        if not question:
            try:
                await update.message.reply_text(
                    "❌ Не удалось получить вопрос из базы данных",
                    reply_markup=reply_markup
                )
            except TelegramTimedOut as timeout_error:
                print_flush(f"[HANDLER ERROR] Таймаут при отправке сообщения об ошибке БД: {timeout_error}")
                logger.error(f"Таймаут при отправке сообщения об ошибке БД: {timeout_error}")
            except Exception as e:
                print_flush(f"[HANDLER ERROR] Ошибка при отправке сообщения об ошибке БД: {e}")
                logger.error(f"Ошибка при отправке сообщения об ошибке БД: {e}")
            return
        
        # Сохраняем вопрос в context для последующей обработки ответа
        context.user_data['current_question'] = {
            'id': question['id'],
            'question': question['question'],
            'topic': question.get('topic', ''),
            'answer': question.get('answer', '')
        }
        
        message = f"❓ <b>Вопрос #{question['id']}</b>\n\n"
        message += f"<b>Тема:</b> {question.get('topic', 'Не указана')}\n\n"
        message += f"<b>Вопрос:</b>\n{question['question']}\n\n"
        message += "💬 <b>Отправь свой ответ текстом, и я оценю его!</b>"
        
        try:
            print_flush(f"[HANDLER] Отправляю вопрос #{question['id']} пользователю")
            await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
            print_flush(f"[HANDLER] Вопрос #{question['id']} успешно отправлен")
        except TelegramTimedOut as timeout_error:
            print_flush(f"[HANDLER ERROR] Таймаут при отправке вопроса пользователю: {timeout_error}")
            logger.error(f"Таймаут при отправке вопроса пользователю: {timeout_error}")
            # Пытаемся отправить упрощенное сообщение без форматирования
            try:
                simple_message = f"❓ Вопрос #{question['id']}\n\nТема: {question.get('topic', 'Не указана')}\n\nВопрос:\n{question['question']}\n\n💬 Отправь свой ответ текстом, и я оценю его!"
                await update.message.reply_text(simple_message, reply_markup=reply_markup)
                print_flush(f"[HANDLER] Упрощенный вопрос #{question['id']} отправлен после таймаута")
            except Exception as retry_error:
                print_flush(f"[HANDLER ERROR] Не удалось отправить даже упрощенный вопрос: {retry_error}")
                logger.error(f"Не удалось отправить даже упрощенный вопрос: {retry_error}")
        except Exception as e:
            print_flush(f"[HANDLER ERROR] Ошибка при отправке вопроса пользователю: {e}")
            logger.error(f"Ошибка при отправке вопроса пользователю: {e}")
            # Пытаемся отправить упрощенное сообщение без форматирования
            try:
                simple_message = f"❓ Вопрос #{question['id']}\n\nТема: {question.get('topic', 'Не указана')}\n\nВопрос:\n{question['question']}\n\n💬 Отправь свой ответ текстом, и я оценю его!"
                await update.message.reply_text(simple_message, reply_markup=reply_markup)
            except Exception as retry_error:
                print_flush(f"[HANDLER ERROR] Не удалось отправить даже упрощенный вопрос: {retry_error}")
                logger.error(f"Не удалось отправить даже упрощенный вопрос: {retry_error}")
        return
    
    # Проверяем, есть ли активный вопрос в контексте (пользователь отвечает на вопрос)
    if 'current_question' in context.user_data:
        # Это ответ пользователя на вопрос
        current_question = context.user_data['current_question']
        user_answer = text
        
        # Отправляем сообщение о том, что обрабатываем ответ
        processing_msg = await update.message.reply_text("⏳ Оцениваю твой ответ...", reply_markup=reply_markup)
        
        # Оцениваем ответ через LLM
        if llm_service:
            try:
                import time
                start_time = time.time()
                print_flush(f"Оцениваю ответ пользователя на вопрос #{current_question['id']}")
                # Обертываем синхронный вызов в asyncio.to_thread, чтобы не блокировать event loop
                # Это предотвращает таймауты при длительных запросах к LLM API
                evaluation = await asyncio.to_thread(
                    llm_service.evaluate_answer,
                    question=current_question['question'],
                    user_answer=user_answer,
                    correct_answer=current_question.get('answer')
                )
                
                llm_time = time.time() - start_time
                print_flush(f"[HANDLER] Получена оценка от LLM за {llm_time:.2f} сек: {evaluation[:100]}...")
                logger.info(f"LLM оценка получена за {llm_time:.2f} сек для вопроса #{current_question['id']}")
                
                # Формируем сообщение с оценкой
                response_message = f"📝 <b>Оценка твоего ответа:</b>\n\n{evaluation}"
                
                # Редактируем сообщение "Оцениваю..." на результат
                try:
                    edit_start_time = time.time()
                    print_flush(f"[HANDLER] Редактирую сообщение с результатом оценки (длина: {len(response_message)} символов)")
                    await processing_msg.edit_text(response_message, parse_mode='HTML', reply_markup=reply_markup)
                    edit_time = time.time() - edit_start_time
                    print_flush(f"[HANDLER] Сообщение успешно отредактировано за {edit_time:.2f} сек")
                    logger.info(f"Сообщение отредактировано за {edit_time:.2f} сек")
                except TelegramTimedOut as timeout_error:
                    # Специальная обработка таймаута Telegram API
                    print_flush(f"[HANDLER ERROR] Таймаут при редактировании сообщения в Telegram: {timeout_error}")
                    logger.error(f"Таймаут при редактировании сообщения в Telegram: {timeout_error}")
                    
                    # Пытаемся отредактировать упрощенное сообщение без форматирования
                    try:
                        simple_message = f"📝 Оценка твоего ответа:\n\n{evaluation[:1000]}"  # Ограничиваем длину
                        print_flush(f"[HANDLER] Пытаюсь отредактировать упрощенное сообщение (длина: {len(simple_message)} символов)")
                        await processing_msg.edit_text(simple_message, reply_markup=reply_markup)
                        print_flush("[HANDLER] Упрощенное сообщение отредактировано успешно после таймаута")
                    except Exception as retry_error:
                        print_flush(f"[HANDLER ERROR] Не удалось отредактировать даже упрощенное сообщение: {retry_error}")
                        logger.error(f"Не удалось отредактировать даже упрощенное сообщение: {retry_error}")
                        # В крайнем случае просто логируем ошибку, но не прерываем выполнение
                except Exception as edit_error:
                    # Обработка других ошибок при редактировании сообщения
                    error_str = str(edit_error)
                    error_type = type(edit_error).__name__
                    print_flush(f"[HANDLER ERROR] Ошибка при редактировании сообщения в Telegram: {error_type}: {error_str}")
                    logger.error(f"Ошибка при редактировании сообщения в Telegram: {error_type}: {error_str}")
                    
                    # Пытаемся отредактировать упрощенное сообщение без форматирования
                    try:
                        simple_message = f"📝 Оценка твоего ответа:\n\n{evaluation[:1000]}"  # Ограничиваем длину
                        print_flush(f"[HANDLER] Пытаюсь отредактировать упрощенное сообщение после ошибки")
                        await processing_msg.edit_text(simple_message, reply_markup=reply_markup)
                        print_flush("[HANDLER] Упрощенное сообщение отредактировано успешно после ошибки")
                    except Exception as retry_error:
                        print_flush(f"[HANDLER ERROR] Не удалось отредактировать даже упрощенное сообщение: {retry_error}")
                        logger.error(f"Не удалось отредактировать даже упрощенное сообщение: {retry_error}")
                        # В крайнем случае просто логируем ошибку, но не прерываем выполнение
                
            except UnsupportedRegionError as e:
                # Специальная обработка ошибки недоступности API в регионе
                import traceback
                error_details = traceback.format_exc()
                username = update.message.from_user.username or update.message.from_user.first_name or "unknown"
                user_id = update.message.from_user.id
                
                logger.error(
                    f"OpenAI API недоступен в регионе. "
                    f"Пользователь: {username} (ID: {user_id}), "
                    f"Вопрос ID: {current_question['id']}, "
                    f"Ошибка: {str(e)}\n"
                    f"Детали ошибки:\n{error_details}"
                )
                
                # Редактируем сообщение "Оцениваю..." на сообщение об ошибке
                error_message = (
                    "❌ <b>OpenAI API недоступен в вашем регионе</b>\n\n"
                    "Для работы функции оценки ответов необходимо:\n"
                    "• Использовать VPN\n"
                    "• Или настроить альтернативный LLM API (Yandex GPT, Anthropic Claude и т.д.)\n\n"
                    "Ваш ответ был сохранен в логах."
                )
                try:
                    print_flush(f"[HANDLER] Редактирую сообщение об ошибке региона")
                    await processing_msg.edit_text(error_message, parse_mode='HTML', reply_markup=reply_markup)
                    print(f"[HANDLER] Сообщение об ошибке региона успешно отредактировано")
                except TelegramTimedOut as timeout_error:
                    print_flush(f"[HANDLER ERROR] Таймаут при редактировании сообщения об ошибке региона: {timeout_error}")
                    logger.error(f"Таймаут при редактировании сообщения об ошибке региона: {timeout_error}")
                except Exception as edit_error:
                    print_flush(f"[HANDLER ERROR] Не удалось отредактировать сообщение об ошибке региона: {edit_error}")
                    logger.error(f"Не удалось отредактировать сообщение об ошибке региона: {edit_error}")
            except LLMTimeoutError as e:
                # Специальная обработка ошибки таймаута
                import traceback
                error_details = traceback.format_exc()
                username = update.message.from_user.username or update.message.from_user.first_name or "unknown"
                user_id = update.message.from_user.id
                
                error_msg = (
                    f"Таймаут при оценке ответа. "
                    f"Пользователь: {username} (ID: {user_id}), "
                    f"Вопрос ID: {current_question['id']}, "
                    f"Ошибка: {str(e)}"
                )
                print_flush(f"[HANDLER ERROR] {error_msg}")
                print_flush(f"[HANDLER ERROR] Детали ошибки:\n{error_details}")
                logger.error(
                    f"Таймаут при оценке ответа. "
                    f"Пользователь: {username} (ID: {user_id}), "
                    f"Вопрос ID: {current_question['id']}, "
                    f"Ошибка: {str(e)}\n"
                    f"Детали ошибки:\n{error_details}"
                )
                
                # Редактируем сообщение "Оцениваю..." на сообщение о таймауте
                timeout_message = (
                    "⏱️ <b>Превышено время ожидания ответа от LLM API</b>\n\n"
                    "Возможные причины:\n"
                    "• Медленное соединение\n"
                    "• Проблемы с прокси\n"
                    "• Перегрузка API сервера\n\n"
                    "Попробуйте позже или проверьте настройки прокси.\n\n"
                    "Ваш ответ был сохранен в логах."
                )
                try:
                    print_flush(f"[HANDLER] Редактирую сообщение о таймауте LLM")
                    await processing_msg.edit_text(timeout_message, parse_mode='HTML', reply_markup=reply_markup)
                    print(f"[HANDLER] Сообщение о таймауте LLM успешно отредактировано")
                except TelegramTimedOut as timeout_error:
                    print_flush(f"[HANDLER ERROR] Таймаут при редактировании сообщения о таймауте LLM: {timeout_error}")
                    logger.error(f"Таймаут при редактировании сообщения о таймауте LLM: {timeout_error}")
                except Exception as edit_error:
                    print(f"[HANDLER ERROR] Не удалось отредактировать сообщение о таймауте: {edit_error}")
                    logger.error(f"Не удалось отредактировать сообщение о таймауте: {edit_error}")
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                error_msg = str(e)
                print_flush(f"[HANDLER ERROR] Ошибка при оценке ответа: {error_msg}")
                print_flush(f"[HANDLER ERROR] Детали ошибки:\n{error_details}")
                # Ограничиваем длину сообщения об ошибке для Telegram
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                
                # Редактируем сообщение "Оцениваю..." на сообщение об ошибке
                error_message = f"❌ Ошибка при оценке ответа: {error_msg}"
                try:
                    print_flush(f"[HANDLER] Редактирую сообщение об общей ошибке")
                    await processing_msg.edit_text(error_message, parse_mode='HTML', reply_markup=reply_markup)
                    print(f"[HANDLER] Сообщение об общей ошибке успешно отредактировано")
                except TelegramTimedOut as timeout_error:
                    print(f"[HANDLER ERROR] Таймаут при редактировании сообщения об общей ошибке: {timeout_error}")
                    logger.error(f"Таймаут при редактировании сообщения об общей ошибке: {timeout_error}")
                except Exception as edit_error:
                    print(f"[HANDLER ERROR] Не удалось отредактировать сообщение об ошибке: {edit_error}")
                    logger.error(f"Не удалось отредактировать сообщение об ошибке: {edit_error}")
        else:
            # Редактируем сообщение "Оцениваю..." на сообщение об отсутствии API ключа
            no_key_message = "❌ Оценка ответов недоступна: LLM_API_KEY не установлен"
            try:
                print_flush(f"[HANDLER] Редактирую сообщение об отсутствии API ключа")
                await processing_msg.edit_text(no_key_message, parse_mode='HTML', reply_markup=reply_markup)
                print_flush(f"[HANDLER] Сообщение об отсутствии API ключа успешно отредактировано")
            except TelegramTimedOut as timeout_error:
                print_flush(f"[HANDLER ERROR] Таймаут при редактировании сообщения об отсутствии API ключа: {timeout_error}")
                logger.error(f"Таймаут при редактировании сообщения об отсутствии API ключа: {timeout_error}")
            except Exception as edit_error:
                print_flush(f"[HANDLER ERROR] Не удалось отредактировать сообщение об отсутствии API ключа: {edit_error}")
                logger.error(f"Не удалось отредактировать сообщение об отсутствии API ключа: {edit_error}")
        
        # Получаем username пользователя
        username = update.message.from_user.username or update.message.from_user.first_name or "unknown"
        
        # Сохраняем лог в БД (всегда, независимо от результата оценки)
        # Делаем это в блоке finally, чтобы гарантировать сохранение даже при ошибках
        try:
            user_answer_preview = user_answer[:50] + "..." if user_answer and len(user_answer) > 50 else (user_answer or "None")
            print_flush(f"[HANDLER] Попытка записи лога: username={username}, question_id={current_question['id']}, user_answer_len={len(user_answer) if user_answer else 0}, user_answer_preview={user_answer_preview}")
            print_flush(f"[HANDLER] user_answer type: {type(user_answer)}, value: {repr(user_answer)}")
            
            db.log_question_answer(
                username=username,
                question_id=current_question['id'],
                user_answer=user_answer  # Передаем ответ пользователя
            )
            print_flush(f"[HANDLER] Лог успешно записан в БД")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print_flush(f"[HANDLER ERROR] КРИТИЧЕСКАЯ ОШИБКА при записи лога: {error_details}")
            logger.error(f"КРИТИЧЕСКАЯ ОШИБКА при записи лога: {error_details}")
            # Не прерываем выполнение, но логируем детально
        finally:
            # Очищаем текущий вопрос из контекста в любом случае
            if 'current_question' in context.user_data:
                del context.user_data['current_question']
        
        return
    else:
        # Если пользователь отправил другой текст и нет активного вопроса, показываем подсказку
        try:
            await update.message.reply_text(
                "Используй кнопку '🎲 Случайный вопрос' для получения вопроса!",
                reply_markup=reply_markup
            )
        except TelegramTimedOut as timeout_error:
            print_flush(f"[HANDLER ERROR] Таймаут при отправке подсказки: {timeout_error}")
            logger.error(f"Таймаут при отправке подсказки: {timeout_error}")
        except Exception as e:
            print_flush(f"[HANDLER ERROR] Ошибка при отправке подсказки: {e}")
            logger.error(f"Ошибка при отправке подсказки: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    import traceback
    error_details = traceback.format_exc()
    print_flush(f"Ошибка при обработке обновления: {context.error}")
    print_flush(f"Детали ошибки: {error_details}")
    
    if update and update.message:
        try:
            await update.message.reply_text(
                f"❌ Произошла ошибка: {str(context.error)}\n\nПопробуйте позже или используйте /help",
                reply_markup=reply_markup
            )
        except TelegramTimedOut as timeout_error:
            print_flush(f"[ERROR HANDLER] Таймаут при отправке сообщения об ошибке: {timeout_error}")
            logger.error(f"Таймаут при отправке сообщения об ошибке: {timeout_error}")
        except Exception as e:
            print_flush(f"[ERROR HANDLER] Не удалось отправить сообщение об ошибке: {e}")
            logger.error(f"Не удалось отправить сообщение об ошибке: {e}")

