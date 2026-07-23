from datetime import date, datetime
from unittest import TestCase
from uuid import UUID

from parameterized import parameterized

from ddsql.serializers import PostgresSerializer

serializer = PostgresSerializer()


class TestPostgresSerializer(TestCase):
    @parameterized.expand(
        (
            ("UMIDIGI Romance's Umi", "'UMIDIGI Romance''s Umi'"),
            ('C:\\path', "E'C:\\\\path'"),
            ("a\\'b", "E'a\\\\''b'"),
            ('line1\nline2\tend', "E'line1\\nline2\\tend'"),
            ('\b\f\r', "E'\\b\\f\\r'"),
            ('\x01\x1b\x7f', "E'\\x01\\x1B\\x7F'"),
            ('Привет 🌍 "quotes"', '\'Привет 🌍 "quotes"\''),
            ('', "''"),
        )
    )
    def test_serialize_string_escaping(self, value, result):
        # Act & Assert
        self.assertEqual(serializer.serialize_value(value), result)

    def test_serialize_string_nul_raises(self):
        # Act & Assert
        with self.assertRaises(ValueError):
            serializer.serialize_value('bad\x00value')

    def test_serialize_string_is_single_line(self):
        # Arrange
        value = ''.join(chr(code) for code in range(0x01, 0x80))

        # Act
        result = serializer.serialize_value(value)

        # Assert
        self.assertTrue(result.isprintable())

    def test_serialize_collection_with_quoted_strings(self):
        # Act & Assert
        self.assertEqual(serializer.serialize_value(["O'Brien", 'plain']), "('O''Brien', 'plain')")

    def test_serialize_uuid(self):
        # Arrange
        value = '123e4567-e89b-12d3-a456-426614174000'

        # Act & Assert
        self.assertEqual(serializer.serialize_value(UUID(value)), f"'{value}'::uuid")

    def test_serialize_datetime(self):
        # Arrange
        value = '2024-01-15T14:30:45'

        # Act & Assert
        self.assertEqual(serializer.serialize_value(datetime.fromisoformat(value)), f"'{value}'::timestamp")

    def test_serialize_date(self):
        # Arrange
        value = '2024-01-15'

        # Act & Assert
        self.assertEqual(serializer.serialize_value(date.fromisoformat(value)), f"'{value}'::date")
