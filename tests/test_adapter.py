from unittest import IsolatedAsyncioTestCase

from ddsql.query import Query
from tests.data.mock_sql import MockSQL
from tests.data.models import User

query = Query(model=User, text='SELECT * FROM users WHERE user_id = {{ user_id }}')


class TestAdapter(IsolatedAsyncioTestCase):
    def setUp(self):
        self.sql = MockSQL(query=query)
        self.adapter = self.sql.mock_adapter

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
