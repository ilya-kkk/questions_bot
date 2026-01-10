import unittest
from unittest.mock import MagicMock, patch
from app.database import Database

class TestDatabase(unittest.TestCase):

    @patch('app.database.psycopg2.connect')
    def test_get_random_question_with_unlearned_questions(self, mock_connect):
        """
        Test that get_random_question returns a question when there are unlearned questions.
        """
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            {'count': 1},
            {'id': 1, 'question': 'What is your name?', 'topic': 'General', 'answer': 'My name is Bard.'}
        ]
        
        db = Database()
        
        # Act
        question = db.get_random_question(user_id=123)
        
        # Assert
        self.assertIsNotNone(question)
        self.assertEqual(question['id'], 1)
        self.assertEqual(mock_cursor.execute.call_count, 2)

    @patch('app.database.psycopg2.connect')
    def test_get_random_question_when_all_questions_are_learned(self, mock_connect):
        """
        Test that get_random_question returns None when all questions have been learned.
        """
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            {'count': 0},
            {'count': 5}
        ]
        
        db = Database()
        
        # Act
        question = db.get_random_question(user_id=123)
        
        # Assert
        self.assertIsNone(question)
        self.assertEqual(mock_cursor.execute.call_count, 2)

    @patch('app.database.psycopg2.connect')
    def test_get_random_question_when_no_questions_in_database(self, mock_connect):
        """
        Test that get_random_question returns None when there are no questions in the database.
        """
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            {'count': 0},
            {'count': 0}
        ]
        
        db = Database()
        
        # Act
        question = db.get_random_question(user_id=123)
        
        # Assert
        self.assertIsNone(question)
        self.assertEqual(mock_cursor.execute.call_count, 2)

if __name__ == '__main__':
    unittest.main()