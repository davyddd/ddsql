from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from ddquery.query import Query, Result
from tests.helpers.models import User
from tests.helpers.utils import TESTS_TEMPLATES_DIR


def serialize_value(value):
    return f"'{value}'"


class TestQuery(IsolatedAsyncioTestCase):
    def test_initialization_without_text_or_path(self):
        # Act & Assert
        with self.assertRaises(ValueError):
            Query(model=User)

    def test_initialization_without_env_var(self):
        # Act & Assert
        with self.assertRaises(ValueError):
            Query(model=User, path='user.sql')

    async def test_render_template_from_text(self):
        # Arrange
        query = Query(model=User, text="""SELECT * FROM users WHERE user_id = {{ user_id }};""")

        # Act
        result = await query.render_template(params={'user_id': 1})

        # Assert
        self.assertEqual(result, """SELECT * FROM users WHERE user_id = 1;""")

    @patch('ddquery.query.SQL_TEMPLATES_DIR', TESTS_TEMPLATES_DIR)
    async def test_render_template_from_path(self):
        # Arrange
        query = Query(model=User, path='user.sql')

        # Act
        result = await query.render_template(params={'user_id': 1})

        # Assert
        self.assertEqual(result, """SELECT * FROM users WHERE user_id = 1;""")

    async def test_render_template_with_template_functions(self):
        # Arrange
        query = Query(model=User, text="""SELECT * FROM users WHERE name = {{ serialize_value(name) }}""")

        # Act
        result = await query.render_template(params={'name': 'John'}, template_functions={'serialize_value': serialize_value})

        # Assert
        self.assertEqual(result, """SELECT * FROM users WHERE name = 'John'""")

    def test_format_sql(self):
        # Arrange
        sql = """  SELECT * FROM users WHERE user_id = 1 AND name = 'John';   """

        # Act
        formated_sql = Query.format_sql(sql)

        # Assert
        self.assertEqual(formated_sql, """SELECT * FROM users WHERE user_id = 1 AND name = 'John';""")

    def test_build_result(self):
        # Arrange
        query = Query(model=User, text='SELECT * FROM users')
        rows = [{'user_id': 1, 'name': 'John', 'email': 'john@example.com'}]

        # Act
        result = query.build_result(rows)

        # Assert
        self.assertIsInstance(result, Result)
        self.assertEqual(result.rows, rows)
        self.assertEqual(result.model, User)
