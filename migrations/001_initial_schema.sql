-- Миграция 001: Начальная схема базы данных
-- Создает таблицы questions и user_logs

-- Таблица вопросов
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY,
    question TEXT NOT NULL,
    topic TEXT,
    answer TEXT
);

-- Таблица логов ответов пользователей
CREATE TABLE IF NOT EXISTS user_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    username TEXT NOT NULL,
    question_id INTEGER NOT NULL,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- Создаем индекс для быстрого поиска по question_id в логах
CREATE INDEX IF NOT EXISTS idx_user_logs_question_id ON user_logs(question_id);

-- Создаем индекс для быстрого поиска по username в логах
CREATE INDEX IF NOT EXISTS idx_user_logs_username ON user_logs(username);

-- Создаем индекс для быстрого поиска по timestamp в логах
CREATE INDEX IF NOT EXISTS idx_user_logs_timestamp ON user_logs(timestamp);

