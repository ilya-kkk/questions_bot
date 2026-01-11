# Questions Bot

Telegram bot that помогает готовиться к интервью и экзаменам: выдаёт случайные вопросы, показывает ответы и позволяет отмечать вопросы как изученные.

## Возможности

- Случайные вопросы и ответы
- Пометка вопросов как изученных
- Хранение данных в PostgreSQL
- Запуск через Docker Compose

## Требования

- Docker и Docker Compose
- Токен Telegram-бота от @BotFather

## Быстрый старт

1. Создайте файл `.env` в корне проекта:

```bash
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
POSTGRES_DB=app_db
POSTGRES_USER=app_user
POSTGRES_PASSWORD=your_strong_password_here
POSTGRES_PORT=5432
```

2. Запустите контейнеры:

```bash
docker-compose up --build -d
```

3. Примените миграции:

```bash
docker-compose exec app python run_migrations.py
```

4. Импортируйте вопросы:

```bash
docker-compose exec app python import_data.py
```

## Структура проекта

- `app/` — код телеграм-бота
- `migrations/` — SQL-миграции
- `import_data.py` — импорт вопросов из `raw.json`
- `run_migrations.py` — применение миграций

## Тесты

Локальный запуск unit-тестов:
`pip install -r requirements.txt -r requirements-dev.txt`
`pytest -q`

## Остановка

```bash
docker-compose down
```
