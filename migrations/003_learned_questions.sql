-- Миграция 003: Таблица для отмеченных как выученные вопросов и очистка устаревших колонок
-- Создает таблицу learned_questions и удаляет колонку user_answer из старых логов

-- Таблица отмеченных вопросов
CREATE TABLE IF NOT EXISTS learned_questions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username TEXT,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_learned_user_question UNIQUE (user_id, question_id)
);

-- Индекс для быстрого поиска по user_id
CREATE INDEX IF NOT EXISTS idx_learned_questions_user_id ON learned_questions(user_id);

-- Индекс для быстрого поиска по question_id
CREATE INDEX IF NOT EXISTS idx_learned_questions_question_id ON learned_questions(question_id);

-- Удаляем устаревшую колонку user_answer из user_logs, если она была
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'user_logs' 
          AND column_name = 'user_answer'
    ) THEN
        ALTER TABLE user_logs DROP COLUMN user_answer;
    END IF;
END $$;

-- Удаляем устаревшую колонку user_answer из logs, если такая таблица существует
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
          AND table_name = 'logs'
    ) THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'logs' 
              AND column_name = 'user_answer'
        ) THEN
            ALTER TABLE logs DROP COLUMN user_answer;
        END IF;
    END IF;
END $$;


