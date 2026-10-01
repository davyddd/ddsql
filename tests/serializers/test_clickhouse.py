from datetime import date, datetime
from unittest import TestCase
from uuid import UUID

from parameterized import parameterized

from ddsql.serializers import ClickhouseSerializer

serializer = ClickhouseSerializer()


class TestClickhouseSerializer(TestCase):
    @parameterized.expand(
        (
            ("UMIDIGI Romance's Umi", "'UMIDIGI Romance\\'s Umi'"),
            ('C:\\path', "'C:\\\\path'"),
            ("a\\'b", "'a\\\\\\'b'"),
            ('line1\nline2\tend', "'line1\\nline2\\tend'"),
            ('\0\a\b\v\f\r', "'\\0\\a\\b\\v\\f\\r'"),
            ('\x01\x1b\x7f', "'\\x01\\x1B\\x7F'"),
            ('Привет 🌍 "quotes" `ticks`', '\'Привет 🌍 "quotes" `ticks`\''),
            ('', "''"),
        )
    )
    def test_serialize_string_escaping(self, value, result):
        # Act & Assert
        self.assertEqual(serializer.serialize_value(value), result)

    def test_serialize_string_is_single_line(self):
        # Arrange
        value = ''.join(chr(code) for code in range(0x80))

        # Act
        result = serializer.serialize_value(value)

        # Assert
        self.assertTrue(result.isprintable())

    def test_serialize_collection_with_quoted_strings(self):
        # Act & Assert
        self.assertEqual(serializer.serialize_value(["O'Brien", 'plain']), "('O\\'Brien', 'plain')")

    def test_serialize_uuid(self):
        # Arrange
        value = '123e4567-e89b-12d3-a456-426614174000'

        # Act & Assert
        self.assertEqual(serializer.serialize_value(UUID(value)), f"toUUID('{value}')")

    @parameterized.expand(
        (
            ('2024-01-15T14:30:45',),
            ('2026-10-01T12:54:03.352581',),
            ('2026-10-01T12:54:03.352581+00:00',),
            ('2026-10-01T15:54:03.352581+03:00',),
        )
    )
    def test_serialize_datetime(self, value):
        # Act & Assert
        self.assertEqual(serializer.serialize_value(datetime.fromisoformat(value)), f"parseDateTime64BestEffort('{value}', 6)")

    def test_serialize_date(self):
        # Arrange
        value = '2024-01-15'

        # Act & Assert
        self.assertEqual(serializer.serialize_value(date.fromisoformat(value)), f"toDate('{value}')")
