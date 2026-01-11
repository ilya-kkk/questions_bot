import types
from unittest.mock import AsyncMock

import pytest

from app import handlers
from app.messages import INVALID_REQUEST, NO_QUESTIONS, ALL_QUESTIONS_LEARNED

pytestmark = pytest.mark.unit


async def _fake_to_thread(func, *args, **kwargs):
    return func(*args, **kwargs)


def test_question_text_with_answer_includes_fields():
    question = {"id": 5, "question": "What is 2+2?", "topic": "Math", "answer": "4"}
    text = handlers._question_text(question, with_answer=True)

    assert f"#{question['id']}" in text
    assert question["question"] in text
    assert question["topic"] in text
    assert question["answer"] in text


def test_question_text_missing_answer_uses_default():
    question = {"id": 7, "question": "What is 2+2?", "topic": "Math"}
    text = handlers._question_text(question, with_answer=True)

    assert "Ответ не указан" in text


@pytest.mark.asyncio
async def test_handle_callback_query_invalid_data_edits_message():
    query = types.SimpleNamespace(
        data="invalid",
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
    )
    update = types.SimpleNamespace(callback_query=query)
    context = types.SimpleNamespace()

    handler = AsyncMock()
    wrapped = handlers.handle_callback_query(handler)

    await wrapped(update, context)

    handler.assert_not_awaited()
    query.edit_message_text.assert_awaited_once_with(INVALID_REQUEST)


@pytest.mark.asyncio
async def test_handle_callback_query_valid_data_calls_handler():
    query = types.SimpleNamespace(
        data="show_answer:42",
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
    )
    update = types.SimpleNamespace(callback_query=query)
    context = types.SimpleNamespace()

    handler = AsyncMock()
    wrapped = handlers.handle_callback_query(handler)

    await wrapped(update, context)

    handler.assert_awaited_once()
    args, kwargs = handler.await_args
    assert args[0] is update
    assert args[1] is context
    assert args[2] is query
    assert args[3] == 42


@pytest.mark.asyncio
async def test_send_random_question_no_questions(monkeypatch):
    db_stub = types.SimpleNamespace(
        get_total_questions_count=lambda: 0,
        get_random_question=lambda user_id: None,
    )
    chat = types.SimpleNamespace(reply_text=AsyncMock())

    monkeypatch.setattr(handlers, "db", db_stub)
    monkeypatch.setattr(handlers.asyncio, "to_thread", _fake_to_thread)

    await handlers.send_random_question(chat, user_id=123)

    chat.reply_text.assert_awaited_once()
    args, kwargs = chat.reply_text.await_args
    assert args[0] == NO_QUESTIONS
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_send_random_question_all_learned(monkeypatch):
    db_stub = types.SimpleNamespace(
        get_total_questions_count=lambda: 10,
        get_random_question=lambda user_id: None,
    )
    chat = types.SimpleNamespace(reply_text=AsyncMock())

    monkeypatch.setattr(handlers, "db", db_stub)
    monkeypatch.setattr(handlers.asyncio, "to_thread", _fake_to_thread)

    await handlers.send_random_question(chat, user_id=123)

    chat.reply_text.assert_awaited_once()
    args, kwargs = chat.reply_text.await_args
    assert args[0] == ALL_QUESTIONS_LEARNED
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_send_random_question_success(monkeypatch):
    question = {
        "id": 12,
        "question": "What is 2+2?",
        "topic": "Math",
        "answer": "4",
    }
    db_stub = types.SimpleNamespace(
        get_total_questions_count=lambda: 10,
        get_random_question=lambda user_id: question,
    )
    chat = types.SimpleNamespace(reply_text=AsyncMock())

    monkeypatch.setattr(handlers, "db", db_stub)
    monkeypatch.setattr(handlers.asyncio, "to_thread", _fake_to_thread)

    await handlers.send_random_question(chat, user_id=123)

    chat.reply_text.assert_awaited_once()
    args, kwargs = chat.reply_text.await_args
    assert question["question"] in args[0]
    assert question["answer"] not in args[0]
    assert kwargs["parse_mode"] == "HTML"
    markup = kwargs["reply_markup"]
    assert markup.inline_keyboard[0][0].callback_data == f"show_answer:{question['id']}"
