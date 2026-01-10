"""
Обработчики команд и сообщений для телеграм бота (без LLM)
"""
import asyncio
import logging
import sys
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.error import TimedOut as TelegramTimedOut, BadRequest
from telegram.ext import ContextTypes
from app.database import Database
from app.messages import (
    WELCOME, NO_QUESTIONS, ALL_QUESTIONS_LEARNED, QUESTION_NOT_FOUND,
    INVALID_REQUEST, QUESTION_MARKED_LEARNED, QUESTION_ALREADY_MARKED_LEARNED,
    QUESTION_WILL_BE_REPEATED, USE_RANDOM_QUESTION_BUTTON, ERROR_MESSAGE,
    ERROR_WITH_START, LEARNED_STATS
)

logger = logging.getLogger(__name__)

db = Database()

# Reply Keyboard (рядом с полем ввода)
reply_keyboard = [
    [KeyboardButton("🎲 Случайный вопрос"), KeyboardButton("📊 Статистика")]
]
reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)


def handle_callback_query(func):
    """Декоратор для обработки boilerplate кода в callback query хендлерах."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query:
            logger.error(f"query is None in {func.__name__}")
            return

        try:
            await query.answer()
        except BadRequest as e:
            if "too old" in str(e).lower() or "timeout" in str(e).lower() or "invalid" in str(e).lower():
                logger.warning(f"Callback query устарел, продолжаем обработку в {func.__name__}")
            else:
                raise

        try:
            _, question_id_str = query.data.split(":", 1)
            question_id = int(question_id_str)
        except (ValueError, IndexError) as e:
            logger.exception(f"Ошибка парсинга question_id в {func.__name__}: {e}, data={query.data}")
            try:
                await query.edit_message_text(INVALID_REQUEST)
            except BadRequest:
                pass
            return

        return await func(update, context, query, question_id)

    return wrapper


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
        await update.message.reply_text(WELCOME, reply_markup=reply_markup)
    except TelegramTimedOut as timeout_error:
        logger.error(f"Таймаут при отправке приветствия: {timeout_error}")
    except Exception as send_error:
        logger.exception(f"Ошибка при отправке приветствия: {send_error}")


async def send_random_question(chat, user_id: int):
    """Отправляет случайный невыученный вопрос в указанный чат"""
    # Выполняем синхронные вызовы БД в отдельном потоке, чтобы не блокировать event loop
    total_count = await asyncio.to_thread(db.get_total_questions_count)
    if total_count == 0:
        await chat.reply_text(NO_QUESTIONS, reply_markup=reply_markup)
        return
    
    question = await asyncio.to_thread(db.get_random_question, user_id)
    if not question:
        await chat.reply_text(ALL_QUESTIONS_LEARNED, reply_markup=reply_markup)
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
            logger.error("query is None in random_question_callback")
            return
        
        await query.answer()

        user_id = query.from_user.id
        # Выполняем синхронные вызовы БД в отдельном потоке
        total_count = await asyncio.to_thread(db.get_total_questions_count)
        
        if total_count == 0:
            await query.edit_message_text(NO_QUESTIONS)
            return
        
        question = await asyncio.to_thread(db.get_random_question, user_id)

        if not question:
            await query.edit_message_text(ALL_QUESTIONS_LEARNED)
            return

        message = _question_text(question)
        keyboard = [[InlineKeyboardButton("👁 Показать ответ", callback_data=f"show_answer:{question['id']}")]]
        inline_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, parse_mode='HTML', reply_markup=inline_markup)
    except Exception as e:
        logger.exception(f"Ошибка в random_question_callback: {e}")
        if update.callback_query:
            try:
                await update.callback_query.answer(ERROR_MESSAGE)
            except:
                pass


@handle_callback_query
async def show_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, query, question_id: int):
    """Показывает ответ и предлагает отметить выученным/повторить"""
    try:
        # Выполняем синхронные вызовы БД в отдельном потоке
        question = await asyncio.to_thread(db.get_question_by_id, question_id)
        if not question:
            try:
                await query.edit_message_text(QUESTION_NOT_FOUND)
            except:
                pass
            return

        # Логируем показ ответа (не блокируем основной поток)
        user = query.from_user
        username = user.username or user.first_name or f"user_{user.id}"
        await asyncio.to_thread(db.log_user_action, username, question_id)

        message = _question_text(question, with_answer=True)
        keyboard = [
            [
                InlineKeyboardButton("✅ Запомнил", callback_data=f"learned:{question_id}"),
                InlineKeyboardButton("🔁 Повторю", callback_data=f"repeat:{question_id}")
            ]
        ]
        inline_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, parse_mode='HTML', reply_markup=inline_markup)
    except BadRequest as e:
        # Игнорируем ошибки устаревших queries при редактировании
        if "too old" in str(e).lower() or "timeout" in str(e).lower() or "invalid" in str(e).lower():
            logger.warning(f"Callback query устарел при редактировании, игнорируем")
        else:
            raise
    except Exception as e:
        logger.exception(f"Ошибка в show_answer_callback: {e}")


@handle_callback_query
async def mark_learned_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, query, question_id: int):
    """Отмечает вопрос как выученный"""
    try:
        # Выполняем синхронные вызовы БД в отдельном потоке
        question = await asyncio.to_thread(db.get_question_by_id, question_id)
        if not question:
            try:
                await query.edit_message_text(QUESTION_NOT_FOUND)
            except:
                pass
            return

        user = query.from_user
        inserted = await asyncio.to_thread(db.mark_question_learned, user.id, user.username, question_id)
        status_text = QUESTION_MARKED_LEARNED if inserted else QUESTION_ALREADY_MARKED_LEARNED

        # Логируем действие (не блокируем основной поток)
        username = user.username or user.first_name or f"user_{user.id}"
        await asyncio.to_thread(db.log_user_action, username, question_id)

        # Формируем сообщение с вопросом, ответом и статусом
        message = _question_text(question, with_answer=True)
        message += f"\n\n{status_text}"

        # Обновляем сообщение без кнопок
        await query.edit_message_text(message, parse_mode='HTML')
    except BadRequest as e:
        # Игнорируем ошибки устаревших queries при редактировании
        if "too old" in str(e).lower() or "timeout" in str(e).lower() or "invalid" in str(e).lower():
            logger.warning(f"Callback query устарел при редактировании, игнорируем")
        else:
            raise
    except Exception as e:
        logger.exception(f"Ошибка в mark_learned_callback: {e}")


@handle_callback_query
async def repeat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, query, question_id: int):
    """Пользователь выбрал повторить — ничего не пишем в БД"""
    try:
        # Выполняем синхронные вызовы БД в отдельном потоке
        question = await asyncio.to_thread(db.get_question_by_id, question_id)
        if not question:
            try:
                await query.edit_message_text(QUESTION_NOT_FOUND)
            except:
                pass
            return

        # Логируем действие (не блокируем основной поток)
        user = query.from_user
        username = user.username or user.first_name or f"user_{user.id}"
        await asyncio.to_thread(db.log_user_action, username, question_id)

        # Формируем сообщение с вопросом, ответом и статусом
        message = _question_text(question, with_answer=True)
        message += f"\n\n{QUESTION_WILL_BE_REPEATED}"

        # Обновляем сообщение без кнопок
        await query.edit_message_text(message, parse_mode='HTML')
    except BadRequest as e:
        # Игнорируем ошибки устаревших queries при редактировании
        if "too old" in str(e).lower() or "timeout" in str(e).lower() or "invalid" in str(e).lower():
            logger.warning(f"Callback query устарел при редактировании, игнорируем")
        else:
            raise
    except Exception as e:
        logger.exception(f"Ошибка в repeat_callback: {e}")


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений (для Reply Keyboard кнопок)"""
    text = update.message.text

    if text == "🎲 Случайный вопрос":
        user_id = update.message.from_user.id
        await send_random_question(update.message, user_id)
        return
    if text == "📊 Статистика":
        user_id = update.message.from_user.id
        learned_count = await asyncio.to_thread(db.get_learned_questions_count, user_id)
        await update.message.reply_text(
            LEARNED_STATS.format(count=learned_count),
            reply_markup=reply_markup
        )
        return

    try:
        await update.message.reply_text(
            USE_RANDOM_QUESTION_BUTTON,
            reply_markup=reply_markup
        )
    except TelegramTimedOut as timeout_error:
        logger.error(f"Таймаут при отправке подсказки: {timeout_error}")
    except Exception as e:
        logger.exception(f"Ошибка при отправке подсказки: {e}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке обновления: {context.error}", exc_info=context.error)
    
    # Пытаемся отправить сообщение об ошибке
    try:
        error_text = str(context.error)
        if update and update.message:
            await update.message.reply_text(
                ERROR_WITH_START.format(error=error_text),
                reply_markup=reply_markup
            )
        elif update and update.callback_query:
            # Если это callback query, пытаемся ответить на него
            try:
                await update.callback_query.answer(f"❌ Ошибка: {error_text[:50]}", show_alert=True)
            except:
                # Если не получилось ответить на callback, пытаемся отредактировать сообщение
                try:
                    await update.callback_query.edit_message_text(
                        ERROR_WITH_START.format(error=error_text)
                    )
                except:
                    pass
    except TelegramTimedOut as timeout_error:
        logger.error(f"Таймаут при отправке сообщения об ошибке: {timeout_error}")
    except Exception as e:
        logger.exception(f"Не удалось отправить сообщение об ошибке: {e}")
