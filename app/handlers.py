"""
Обработчики команд и сообщений для телеграм бота
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from app.database import Database
from app.llm_service import LLMService

db = Database()

# Инициализируем LLM сервис (может быть None если ключ не установлен)
try:
    llm_service = LLMService()
except ValueError:
    llm_service = None
    print("Предупреждение: LLM_API_KEY не установлен, оценка ответов будет недоступна")

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
            await update.message.reply_text(
                "❌ Не удалось получить вопрос из базы данных",
                reply_markup=reply_markup
            )
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
        
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
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
                print(f"Оцениваю ответ пользователя на вопрос #{current_question['id']}")
                evaluation = llm_service.evaluate_answer(
                    question=current_question['question'],
                    user_answer=user_answer,
                    correct_answer=current_question.get('answer')
                )
                
                print(f"Получена оценка от LLM: {evaluation[:100]}...")
                
                # Удаляем сообщение "Оцениваю..." и отправляем новое с результатом
                try:
                    await processing_msg.delete()
                except:
                    pass  # Игнорируем ошибку удаления, если сообщение уже удалено
                
                # Формируем сообщение с оценкой
                response_message = f"📝 <b>Оценка твоего ответа:</b>\n\n{evaluation}"
                await update.message.reply_text(response_message, parse_mode='HTML', reply_markup=reply_markup)
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Ошибка при оценке ответа: {error_details}")
                error_msg = str(e)
                # Ограничиваем длину сообщения об ошибке для Telegram
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                
                # Удаляем сообщение "Оцениваю..." и отправляем новое с ошибкой
                try:
                    await processing_msg.delete()
                except:
                    pass
                
                await update.message.reply_text(
                    f"❌ Ошибка при оценке ответа: {error_msg}",
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
        else:
            # Удаляем сообщение "Оцениваю..." и отправляем новое
            try:
                await processing_msg.delete()
            except:
                pass
            
            await update.message.reply_text(
                "❌ Оценка ответов недоступна: LLM_API_KEY не установлен",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        
        # Получаем username пользователя
        username = update.message.from_user.username or update.message.from_user.first_name or "unknown"
        
        # Сохраняем лог в БД (всегда, независимо от результата оценки)
        try:
            print(f"Попытка записи лога: username={username}, question_id={current_question['id']}")
            db.log_question_answer(
                username=username,
                question_id=current_question['id']
            )
            print(f"Лог успешно записан в БД")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"КРИТИЧЕСКАЯ ОШИБКА при записи лога: {error_details}")
            # Не прерываем выполнение, но логируем детально
        
        # Очищаем текущий вопрос из контекста
        del context.user_data['current_question']
        
        return
    else:
        # Если пользователь отправил другой текст и нет активного вопроса, показываем подсказку
        await update.message.reply_text(
            "Используй кнопку '🎲 Случайный вопрос' для получения вопроса!",
            reply_markup=reply_markup
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    import traceback
    error_details = traceback.format_exc()
    print(f"Ошибка при обработке обновления: {context.error}")
    print(f"Детали ошибки: {error_details}")
    
    if update and update.message:
        try:
            await update.message.reply_text(
                f"❌ Произошла ошибка: {str(context.error)}\n\nПопробуйте позже или используйте /help",
                reply_markup=reply_markup
            )
        except:
            # Если не удалось отправить сообщение, просто логируем
            pass

