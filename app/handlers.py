"""
Обработчики команд и сообщений для телеграм бота (без LLM)
"""
import logging
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.error import TimedOut as TelegramTimedOut
from telegram.ext import ContextTypes
from app.database import Database

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

# Reply Keyboard (рядом с полем ввода)
reply_keyboard = [
    [KeyboardButton("🎲 Случайный вопрос")]
]
reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)


def _question_text(question: dict, with_answer: bool = False) -> str:
    """Формирует текст сообщения для вопроса (с ответом или без)"""
    message = f"❓ <b>Вопрос #{question['id']}</b>\n\n"
    message += f"<b>Тема:</b> {question.get('topic', 'Не указана')}\n\n"
    message += f"<b>Вопрос:</b>\n{question['question']}\n"
    if with_answer:
        message += f"\n<b>Ответ:</b>\n{question.get('answer', 'Ответ не указан')}"
    return message


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        welcome_message = (
            "👋 Привет! Нажми \"🎲 Случайный вопрос\", чтобы тренироваться.\n"
            "После показа ответа отметь, выучил ли вопрос."
        )
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    except TelegramTimedOut as timeout_error:
        print_flush(f"[HANDLER ERROR] Таймаут при отправке приветствия: {timeout_error}")
        logger.error(f"Таймаут при отправке приветствия: {timeout_error}")
    except Exception as send_error:
        print_flush(f"[HANDLER ERROR] Ошибка при отправке приветствия: {send_error}")
        logger.error(f"Ошибка при отправке приветствия: {send_error}")


async def send_random_question(chat, user_id: int):
    """Отправляет случайный невыученный вопрос в указанный чат"""
    total_count = db.get_total_questions_count()
    if total_count == 0:
        await chat.reply_text(
            "❌ В базе данных нет вопросов.\n"
            "Добавьте вопросы через импорт данных.",
            reply_markup=reply_markup
        )
        return
    
    question = db.get_random_question(user_id)
    if not question:
        await chat.reply_text(
            "Все вопросы уже отмечены как выученные! 🎉\n"
            "Можно сбросить отметки через БД, чтобы повторить заново.",
            reply_markup=reply_markup
        )
        return

    message = _question_text(question)
    keyboard = [[InlineKeyboardButton("👁 Показать ответ", callback_data=f"show_answer:{question['id']}")]]
    inline_markup = InlineKeyboardMarkup(keyboard)
    await chat.reply_text(message, parse_mode='HTML', reply_markup=inline_markup)


async def random_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия inline 'Случайный вопрос'"""
    try:
        query = update.callback_query
        if not query:
            print_flush("[HANDLER ERROR] query is None in random_question_callback")
            return
        
        await query.answer()

        user_id = query.from_user.id
        total_count = db.get_total_questions_count()
        
        if total_count == 0:
            await query.edit_message_text(
                "❌ В базе данных нет вопросов.\n"
                "Добавьте вопросы через импорт данных."
            )
            return
        
        question = db.get_random_question(user_id)

        if not question:
            await query.edit_message_text(
                "Все вопросы уже отмечены как выученные! 🎉\n"
                "Можно сбросить отметки через БД, чтобы повторить заново."
            )
            return

        message = _question_text(question)
        keyboard = [[InlineKeyboardButton("👁 Показать ответ", callback_data=f"show_answer:{question['id']}")]]
        inline_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, parse_mode='HTML', reply_markup=inline_markup)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print_flush(f"[HANDLER ERROR] Ошибка в random_question_callback: {e}")
        print_flush(f"[HANDLER ERROR] Детали: {error_details}")
        logger.error(f"Ошибка в random_question_callback: {e}\n{error_details}")
        if update.callback_query:
            try:
                await update.callback_query.answer("❌ Произошла ошибка. Попробуйте позже.")
            except:
                pass


async def show_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает ответ и предлагает отметить выученным/повторить"""
    try:
        query = update.callback_query
        if not query:
            print_flush("[HANDLER ERROR] query is None in show_answer_callback")
            return
        
        await query.answer()

        try:
            _, question_id_str = query.data.split(":", 1)
            question_id = int(question_id_str)
        except Exception as e:
            print_flush(f"[HANDLER ERROR] Ошибка парсинга question_id: {e}, data={query.data}")
            await query.edit_message_text("❌ Некорректный запрос")
            return

        question = db.get_question_by_id(question_id)
        if not question:
            await query.edit_message_text("❌ Вопрос не найден в базе")
            return

        message = _question_text(question, with_answer=True)
        keyboard = [
            [
                InlineKeyboardButton("✅ Запомнил", callback_data=f"learned:{question_id}"),
                InlineKeyboardButton("🔁 Повторю", callback_data=f"repeat:{question_id}")
            ]
        ]
        inline_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, parse_mode='HTML', reply_markup=inline_markup)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print_flush(f"[HANDLER ERROR] Ошибка в show_answer_callback: {e}")
        print_flush(f"[HANDLER ERROR] Детали: {error_details}")
        logger.error(f"Ошибка в show_answer_callback: {e}\n{error_details}")
        if update.callback_query:
            try:
                await update.callback_query.answer("❌ Произошла ошибка. Попробуйте позже.")
            except:
                pass


async def mark_learned_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмечает вопрос как выученный"""
    try:
        query = update.callback_query
        if not query:
            print_flush("[HANDLER ERROR] query is None in mark_learned_callback")
            return
        
        await query.answer()

        try:
            _, question_id_str = query.data.split(":", 1)
            question_id = int(question_id_str)
        except Exception as e:
            print_flush(f"[HANDLER ERROR] Ошибка парсинга question_id: {e}, data={query.data}")
            await query.edit_message_text("❌ Некорректный запрос")
            return

        user = query.from_user
        inserted = db.mark_question_learned(user.id, user.username, question_id)
        status_text = "✅ Вопрос отмечен как выученный" if inserted else "✅ Уже был отмечен как выученный"

        await query.edit_message_text(f"{status_text}\n\nИспользуй кнопку '🎲 Случайный вопрос', чтобы получить новый вопрос.")
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print_flush(f"[HANDLER ERROR] Ошибка в mark_learned_callback: {e}")
        print_flush(f"[HANDLER ERROR] Детали: {error_details}")
        logger.error(f"Ошибка в mark_learned_callback: {e}\n{error_details}")
        if update.callback_query:
            try:
                await update.callback_query.answer("❌ Произошла ошибка. Попробуйте позже.")
            except:
                pass


async def repeat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пользователь выбрал повторить — ничего не пишем в БД"""
    try:
        query = update.callback_query
        if not query:
            print_flush("[HANDLER ERROR] query is None in repeat_callback")
            return
        
        await query.answer()

        await query.edit_message_text("Ок, повторим позже. Используй кнопку '🎲 Случайный вопрос', чтобы взять другой вопрос.")
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print_flush(f"[HANDLER ERROR] Ошибка в repeat_callback: {e}")
        print_flush(f"[HANDLER ERROR] Детали: {error_details}")
        logger.error(f"Ошибка в repeat_callback: {e}\n{error_details}")
        if update.callback_query:
            try:
                await update.callback_query.answer("❌ Произошла ошибка. Попробуйте позже.")
            except:
                pass


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений (для Reply Keyboard кнопок)"""
    text = update.message.text

    if text == "🎲 Случайный вопрос":
        user_id = update.message.from_user.id
        await send_random_question(update.message, user_id)
        return

    try:
        await update.message.reply_text(
            "Используй кнопку '🎲 Случайный вопрос', чтобы получить вопрос.",
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
    error_str = str(context.error) if context.error else "Неизвестная ошибка"
    error_type = type(context.error).__name__ if context.error else "Unknown"
    
    print_flush(f"[ERROR HANDLER] Ошибка при обработке обновления: {error_type}: {error_str}")
    print_flush(f"[ERROR HANDLER] Детали ошибки: {error_details}")
    logger.error(f"Ошибка при обработке обновления: {error_type}: {error_str}\n{error_details}")
    
    # Пытаемся отправить сообщение об ошибке
    try:
        if update and update.message:
            await update.message.reply_text(
                f"❌ Произошла ошибка: {error_str}\n\nПопробуйте позже или используйте /start",
                reply_markup=reply_markup
            )
        elif update and update.callback_query:
            # Если это callback query, пытаемся ответить на него
            try:
                await update.callback_query.answer(f"❌ Ошибка: {error_str[:50]}", show_alert=True)
            except:
                # Если не получилось ответить на callback, пытаемся отредактировать сообщение
                try:
                    await update.callback_query.edit_message_text(
                        f"❌ Произошла ошибка: {error_str}\n\nПопробуйте позже."
                    )
                except:
                    pass
    except TelegramTimedOut as timeout_error:
        print_flush(f"[ERROR HANDLER] Таймаут при отправке сообщения об ошибке: {timeout_error}")
        logger.error(f"Таймаут при отправке сообщения об ошибке: {timeout_error}")
    except Exception as e:
        print_flush(f"[ERROR HANDLER] Не удалось отправить сообщение об ошибке: {e}")
        logger.error(f"Не удалось отправить сообщение об ошибке: {e}")

