from collections.abc import Hashable, Sequence
from typing import Any
from unittest import IsolatedAsyncioTestCase

from ddsql.adapter import Adapter, AdapterDescriptor
from ddsql.query import Query
from ddsql.serializers import BaseSerializer
from ddsql.sqlbase import SQLBase
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
        assert user is not None
        self.assertEqual(user.user_id, 1)
        self.assertEqual(user.name, 'Test User')
        self.assertIsNone(user.email)

    async def test_using(self):
        # Arrange
        class Executions:
            dbs: list[Hashable | None] = []

        class RoutingAdapter(Adapter):
            serializer = BaseSerializer()

            async def _execute(self) -> Sequence[dict[str, Any]]:
                Executions.dbs.append(self.db)
                return [{'user_id': 1, 'name': 'Test User', 'email': None}]

        class RoutingSQL(SQLBase):
            adapter: RoutingAdapter = AdapterDescriptor(RoutingAdapter)  # type: ignore

        sql = RoutingSQL(query=query)

        # Act
        await sql.adapter.execute()
        await sql.adapter.using('replica').execute()
        await sql.adapter.execute()

        # Assert: the database is chosen per call, a fresh adapter is bound on every attribute access
        self.assertEqual(Executions.dbs, [None, 'replica', None])
        self.assertIsNone(sql.adapter.db)

    def test_abstract_adapter_needs_no_serializer(self):
        # Act & Assert: only concrete adapters are validated
        class AbstractAdapter(Adapter):
            pass

        with self.assertRaises(NotImplementedError):

            class ConcreteAdapterWithoutSerializer(AbstractAdapter):
                async def _execute(self) -> Sequence[dict[str, Any]]:
                    return []
