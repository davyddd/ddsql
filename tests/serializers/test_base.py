from datetime import date, datetime
from decimal import Decimal
from enum import Enum, IntEnum
from unittest import TestCase
from uuid import UUID

from parameterized import parameterized

from ddsql.serializers import BaseSerializer

serializer = BaseSerializer()
collection = (1, 'hello', None, False)
serialized_collection = "(1, 'hello', NULL, false)"


class CustomObject:
    pass


class Kind(str, Enum):  # noqa: UP042 - the mixin, not `enum.StrEnum`, is what is under test
    ADMIN = 'admin'


class IntMixinKind(int, Enum):
    ONE = 1


class Level(IntEnum):
    LOW = 1


class PlainKind(Enum):
    AT = datetime(2024, 1, 15, 14, 30, 45)
    ID = UUID('123e4567-e89b-12d3-a456-426614174000')


class ProfileId(UUID):
    pass


class Slug(str):
    pass


class TestBaseSerializer(TestCase):
    def test_serialize_none(self):
        # Act & Assert
        self.assertEqual(serializer.serialize_value(None), 'NULL')

    @parameterized.expand(((True, 'true'), (False, 'false')))
    def test_serialize_bool(self, value, result):
        # Act & Assert
        self.assertEqual(serializer.serialize_value(value), result)

    @parameterized.expand(((42, '42'), (1.5, '1.5'), (Decimal('123.45'), '123.45')))
    def test_serialize_number(self, value, result):
        # Act & Assert
        self.assertEqual(serializer.serialize_value(value), result)

    def test_serialize_string(self):
        # Arrange
        value = 'some string'

        # Act & Assert
        self.assertEqual(serializer.serialize_value(value), f"'{value}'")

    @parameterized.expand(
        (
            ("UMIDIGI Romance's Umi", "'UMIDIGI Romance''s Umi'"),
            ('C:\\path', "'C:\\path'"),
            ("a\\'b", "'a\\''b'"),
            ('line1\nline2\tend', "'line1\nline2\tend'"),
            ('', "''"),
        )
    )
    def test_serialize_string_escaping(self, value, result):
        # Act & Assert
        self.assertEqual(serializer.serialize_value(value), result)

    def test_serialize_collection_with_quoted_strings(self):
        # Act & Assert
        self.assertEqual(serializer.serialize_value(["O'Brien", 'plain']), "('O''Brien', 'plain')")

    def test_serialize_uuid(self):
        # Arrange
        value = '123e4567-e89b-12d3-a456-426614174000'

        # Act & Assert
        self.assertEqual(serializer.serialize_value(UUID(value)), f"'{value}'")

    def test_serialize_datetime(self):
        # Arrange
        value = '2024-01-15T14:30:45'

        # Act & Assert
        self.assertEqual(serializer.serialize_value(datetime.fromisoformat(value)), f"'{value}'")

    def test_serialize_date(self):
        # Arrange
        value = '2024-01-15'

        # Act & Assert
        self.assertEqual(serializer.serialize_value(date.fromisoformat(value)), f"'{value}'")

    @parameterized.expand((list, tuple))
    def test_serialize_collection_simple(self, python_class):
        # Assert & Assert
        self.assertEqual(serializer.serialize_value(python_class(collection)), serialized_collection)

    @parameterized.expand((set, frozenset))
    def test_serialize_collection_set(self, python_class):
        # Assert & Assert
        self.assertIsInstance(serializer.serialize_value(python_class(collection)), str)

    def test_serialize_collection_empty(self):
        # Assert & Assert
        self.assertEqual(serializer.serialize_value([]), '()')

    @parameterized.expand((CustomObject, dict, bytes, bytearray))
    def test_serialize_other_object(self, python_class):
        # Act & Assert
        with self.assertRaises(NotImplementedError):
            serializer.serialize_value(python_class())

    @parameterized.expand(
        (
            (Kind.ADMIN, "'admin'"),
            (IntMixinKind.ONE, '1'),
            (Level.LOW, '1'),
            (PlainKind.AT, "'2024-01-15T14:30:45'"),
            (PlainKind.ID, "'123e4567-e89b-12d3-a456-426614174000'"),
        )
    )
    def test_serialize_enum_member_by_its_value(self, value, result):
        # `f'{IntMixinKind.ONE}'` is 'IntMixinKind.ONE'
        self.assertEqual(serializer.serialize_value(value), result)

    @parameterized.expand(
        (
            (Slug('admin'), "'admin'"),
            (ProfileId('123e4567-e89b-12d3-a456-426614174000'), "'123e4567-e89b-12d3-a456-426614174000'"),
        )
    )
    def test_serialize_subclass_as_its_base_type(self, value, result):
        # Act & Assert
        self.assertEqual(serializer.serialize_value(value), result)

    def test_serialize_collection_of_enum_members(self):
        # Act & Assert
        self.assertEqual(serializer.serialize_value((Kind.ADMIN, Level.LOW)), "('admin', 1)")
