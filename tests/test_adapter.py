from unittest import IsolatedAsyncioTestCase
from uuid import UUID

from ddquery.query import Query
from tests.data.mock_sql import MockSQL
from tests.data.models import User

query = Query(model=User, text='SELECT * FROM users WHERE user_id = {{ user_id }}')


class TestAdapter(IsolatedAsyncioTestCase):
    def setUp(self):
        self.sql = MockSQL(query=query)
        self.adapter = self.sql.mock_adapter

    def test_get_params(self):
        # Arrange
        uuid_string = '123e4567-e89b-12d3-a456-426614174000'

        # Act
        self.sql.with_params(user_id=1, name='Test User', some_uuid=UUID(uuid_string))
        serialized_params = self.adapter.get_params()

        # Assert
        self.assertEqual(serialized_params['user_id'], '1')
        self.assertEqual(serialized_params['name'], "'Test User'")
        self.assertEqual(serialized_params['some_uuid'], f"'{uuid_string}'")

    async def test_get_query(self):
        # Act
        self.sql.with_params(user_id=1)
        sql_query = await self.adapter.get_query()

        # Assert
        self.assertEqual(sql_query, 'SELECT * FROM users WHERE user_id = 1')

    async def test_execute(self):
        # Act
        result = await self.adapter.execute()
        user = result.get()
        users = result.get_list()

        # Assert
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(len(users), 1)
        self.assertEqual(user.user_id, 1)
        self.assertEqual(user.name, 'Test User')
        self.assertIsNone(user.email)
