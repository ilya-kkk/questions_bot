"""
Обработчики команд и сообщений для телеграм бота
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.database import Database

db = Database()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        welcome_message = (
            "👋 Привет вкатун! Я бот чтобы ты наконецто заботал все вопросы и прошел собес на 300к наносек.\n\n"
        )
        await update.message.reply_text(welcome_message)
    except Exception as e:
        print(f"Ошибка в start handler: {e}")
        if update and update.message:
            await update.message.reply_text("❌ Произошла ошибка при обработке команды")

async def random_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия на кнопку 'Случайный вопрос'"""
    query = update.callback_query
    await query.answer()
    
    question = db.get_random_question()
    
    if not question:
        await query.edit_message_text("❌ Не удалось получить вопрос из базы данных")
        return
    
    message = f"❓ <b>Вопрос #{question['id']}</b>\n\n"
    message += f"<b>Тема:</b> {question.get('topic', 'Не указана')}\n\n"
    message += f"<b>Вопрос:</b>\n{question['question']}\n\n"
    
    if question.get('answer'):
        message += f"<b>Ответ:</b>\n{question['answer']}"
    else:
        message += "⚠️ Ответ отсутствует"
    
    # Создаем кнопку для обновления сообщения
    keyboard = [[InlineKeyboardButton("🎲 Случайный вопрос", callback_data="random_question")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    print(f"Ошибка при обработке обновления: {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "❌ Произошла ошибка. Попробуйте позже или используйте /help"
        )

