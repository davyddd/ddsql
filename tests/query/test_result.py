from unittest import TestCase

from ddquery.query import Result
from tests.data.models import User


class TestResult(TestCase):
    def test_empty(self):
        # Arrange
        result = Result(rows=[], model=User)

        # Act
        user = result.get()
        users = result.get_list()

        # Assert
        self.assertIsNone(user)
        self.assertEqual(users, ())

    def test_fill(self):
        # Arrange
        rows = [
            {'user_id': 1, 'name': 'John', 'email': 'john@example.com'},
            {'user_id': 2, 'name': 'Jane', 'email': 'jane@example.com'},
        ]
        result = Result(rows=rows, model=User)

        # Act
        user = result.get()
        users = result.get_list()

        # Assert
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, 1)
        self.assertEqual(user.name, 'John')
        self.assertEqual(user.email, 'john@example.com')

        self.assertEqual(len(users), 2)
        self.assertEqual(users[0], user)
        self.assertEqual(users[1].user_id, 2)
        self.assertEqual(users[1].name, 'Jane')
        self.assertEqual(users[1].email, 'jane@example.com')
