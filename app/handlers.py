"""
Обработчики команд и сообщений для телеграм бота
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from app.database import Database

db = Database()

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
            "Используй кнопку ниже, чтобы получить случайный вопрос!"
        )
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    except Exception as e:
        print(f"Ошибка в start handler: {e}")
        if update and update.message:
            await update.message.reply_text("❌ Произошла ошибка при обработке команды", reply_markup=reply_markup)

async def random_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия на inline кнопку 'Случайный вопрос'"""
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
    inline_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=inline_markup)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений (для Reply Keyboard кнопок)"""
    text = update.message.text
    
    if text == "🎲 Случайный вопрос":
        question = db.get_random_question()
        
        if not question:
            await update.message.reply_text(
                "❌ Не удалось получить вопрос из базы данных",
                reply_markup=reply_markup
            )
            return
        
        message = f"❓ <b>Вопрос #{question['id']}</b>\n\n"
        message += f"<b>Тема:</b> {question.get('topic', 'Не указана')}\n\n"
        message += f"<b>Вопрос:</b>\n{question['question']}\n\n"
        
        if question.get('answer'):
            message += f"<b>Ответ:</b>\n{question['answer']}"
        else:
            message += "⚠️ Ответ отсутствует"
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
    else:
        # Если пользователь отправил другой текст, показываем подсказку
        await update.message.reply_text(
            "Используй кнопку '🎲 Случайный вопрос' для получения вопроса!",
            reply_markup=reply_markup
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    print(f"Ошибка при обработке обновления: {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "❌ Произошла ошибка. Попробуйте позже или используйте /help"
        )

