-- Миграция 002: Добавление колонки user_answer в таблицы логов
-- Добавляет колонку user_answer для хранения ответов пользователей

-- Добавляем колонку user_answer в таблицу user_logs (если она существует)
ALTER TABLE IF EXISTS user_logs 
ADD COLUMN IF NOT EXISTS user_answer TEXT;

-- Добавляем колонку user_answer в таблицу logs (для обратной совместимости, если она существует)
ALTER TABLE IF EXISTS logs 
ADD COLUMN IF NOT EXISTS user_answer TEXT;

-- Комментарий к колонке для документации
COMMENT ON COLUMN user_logs.user_answer IS 'Ответ пользователя на вопрос';
COMMENT ON COLUMN logs.user_answer IS 'Ответ пользователя на вопрос (устаревшая таблица)';

