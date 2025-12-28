# Questions Bot

Телеграм бот для работы с вопросами и ответами из базы данных PostgreSQL.

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

3. Отредактируйте `.env` и укажите:
   - `BOT_TOKEN` - токен вашего бота (получить у [@BotFather](https://t.me/BotFather))
   - Параметры подключения к базе данных

4. Убедитесь, что база данных запущена:
```bash
docker-compose up -d
```

5. Импортируйте данные в базу:
```bash
python import_data.py
```

## Запуск бота

```bash
python -m app.bot
```

или

```bash
python app/bot.py
```

## Команды бота

- `/start` - Начать работу с ботом
- `/help` - Показать справку
- `/random` - Получить случайный вопрос с ответом
- `/search <текст>` - Найти вопросы по ключевому слову
- `/topics` - Показать все доступные темы

## Структура проекта

```
questions_bot/
├── app/
│   ├── __init__.py
│   ├── bot.py          # Основной файл бота
│   ├── config.py       # Конфигурация
│   ├── database.py     # Работа с БД
│   └── handlers.py     # Обработчики команд
├── import_data.py      # Скрипт импорта данных
├── requirements.txt    # Зависимости
├── docker-compose.yaml # Конфигурация PostgreSQL
└── .env.example        # Пример конфигурации
```

