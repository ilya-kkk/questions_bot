
import unittest
from unittest.mock import MagicMock, patch
from app.database import Database

class TestSimple(unittest.TestCase):

    @patch('app.database.psycopg2.connect')
    def test_get_connection(self, mock_connect):
        """
        Test that get_connection calls psycopg2.connect
        """
        db = Database()
        db.get_connection()
        mock_connect.assert_called_once()

if __name__ == '__main__':
    unittest.main()
