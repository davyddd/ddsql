from datetime import date, datetime
from unittest import TestCase
from uuid import UUID

from ddsql.serializers import ClickhouseSerializer

serializer = ClickhouseSerializer()


class TestClickhouseSerializer(TestCase):
    def test_serialize_uuid(self):
        # Arrange
        value = '123e4567-e89b-12d3-a456-426614174000'

        # Act & Assert
        self.assertEqual(serializer.serialize_value(UUID(value)), f"toUUID('{value}')")

    def test_serialize_datetime(self):
        # Arrange
        value = '2024-01-15T14:30:45'

        # Act & Assert
        self.assertEqual(serializer.serialize_value(datetime.fromisoformat(value)), f"parseDateTimeBestEffort('{value}')")

    def test_serialize_date(self):
        # Arrange
        value = '2024-01-15'

        # Act & Assert
        self.assertEqual(serializer.serialize_value(date.fromisoformat(value)), f"toDate('{value}')")
