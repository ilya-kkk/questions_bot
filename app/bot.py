#!/usr/bin/env python3
"""
Основной файл телеграм бота для работы с вопросами и ответами
"""
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from app.config import BOT_TOKEN
from app.database import Database
from app.handlers import (
    start,
    random_question_callback,
    handle_text_message,
    error_handler
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен! Создайте файл .env и добавьте BOT_TOKEN")
        return
    
    # Создаем таблицу user_logs если её нет
    db = Database()
    try:
        db.create_logs_table()
        logger.info("Таблица user_logs проверена/создана")
    except Exception as e:
        logger.warning(f"Не удалось создать таблицу user_logs: {e}")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    
    # Регистрируем обработчик текстовых сообщений (для Reply Keyboard)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Регистрируем обработчик callback кнопок (для Inline Keyboard)
    application.add_handler(
        CallbackQueryHandler(random_question_callback, pattern="^random_question$")
    )
    
    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

