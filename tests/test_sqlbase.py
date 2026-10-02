from unittest import TestCase

from ddsql.adapter import AdapterDescriptor
from ddsql.query import Query
from ddsql.sqlbase import SQLBase
from tests.data.mock_sql import MockAdapter, MockSQL
from tests.data.models import User

query = Query(model=User, text='SELECT * FROM users WHERE user_id = {{ user_id }}')


class TestSQLBase(TestCase):
    def setUp(self):
        self.sql = MockSQL(query=query)

    def test_init(self):
        # Act & Assert
        self.assertEqual(self.sql.query, query)
        self.assertEqual(self.sql.params, {})

    def test_with_params_adds_params(self):
        # Act
        sql = self.sql.with_params(user_id=1)

        # Assert
        self.assertIs(self.sql, sql)  # Verify it returns self
        self.assertEqual(self.sql.params, {'user_id': 1})

    def test_with_params_merges_params(self):
        # Act
        self.sql.with_params(user_id=1)
        self.sql.with_params(user_id=2)

        # Assert
        self.assertEqual(self.sql.params, {'user_id': 2})

    def test_with_params_chain(self):
        # Act
        self.sql.with_params(user_id=1).with_params(name='John').with_params(email='john@example.com')

        # Assert
        self.assertEqual(self.sql.params, {'user_id': 1, 'name': 'John', 'email': 'john@example.com'})

    def test_adapter_descriptor_access(self):
        # Act & Assert
        self.assertIsInstance(MockSQL.mock_adapter, AdapterDescriptor)
        self.assertIsInstance(self.sql.mock_adapter, MockAdapter)
        self.assertIs(self.sql.mock_adapter.sql, self.sql)

    def test_subclass_inherits_adapters(self):
        # Act
        class InheritedSQL(MockSQL):
            pass

        # Assert
        self.assertTrue(InheritedSQL.has_adapters)
        self.assertIsInstance(InheritedSQL(query=query).mock_adapter, MockAdapter)

    def test_subclass_without_adapters(self):
        # Act & Assert
        with self.assertRaises(NotImplementedError):

            class NoAdaptersSQL(SQLBase):
                pass
