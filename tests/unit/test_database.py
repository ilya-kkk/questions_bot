from unittest.mock import MagicMock

import pytest

from app.database import Database

pytestmark = pytest.mark.unit


def _make_connection(mock_cursor):
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_cursor.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


def test_get_random_question_returns_question(monkeypatch):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        {"count": 3},
        {"id": 2, "question": "What is 2+2?", "topic": "Math", "answer": "4"},
    ]
    mock_conn = _make_connection(mock_cursor)

    monkeypatch.setattr("app.database.psycopg2.connect", lambda **kwargs: mock_conn)
    randint_mock = MagicMock(return_value=1)
    monkeypatch.setattr("app.database.random.randint", randint_mock)

    db = Database()
    question = db.get_random_question(user_id=123)

    assert question is not None
    assert question["id"] == 2
    randint_mock.assert_called_once_with(0, 2)
    assert mock_cursor.execute.call_count == 2


def test_get_random_question_when_all_learned_returns_none(monkeypatch):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        {"count": 0},
        {"count": 5},
    ]
    mock_conn = _make_connection(mock_cursor)

    monkeypatch.setattr("app.database.psycopg2.connect", lambda **kwargs: mock_conn)
    randint_mock = MagicMock()
    monkeypatch.setattr("app.database.random.randint", randint_mock)

    db = Database()
    question = db.get_random_question(user_id=123)

    assert question is None
    randint_mock.assert_not_called()
    assert mock_cursor.execute.call_count == 2


def test_mark_question_learned_returns_true_when_inserted(monkeypatch):
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_conn = _make_connection(mock_cursor)

    monkeypatch.setattr("app.database.psycopg2.connect", lambda **kwargs: mock_conn)

    db = Database()
    result = db.mark_question_learned(user_id=1, username="user", question_id=10)

    assert result is True
    mock_conn.commit.assert_called_once()
    assert mock_cursor.execute.call_count == 1
