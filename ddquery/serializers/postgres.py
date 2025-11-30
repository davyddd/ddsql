from datetime import date, datetime
from typing import Iterable
from uuid import UUID

from ddquery.serializers import BaseSerializer


class PostgresSerializer(BaseSerializer):
    @staticmethod
    def serialize_uuid(value: UUID) -> str:
        return f"'{value}'::uuid"

    @staticmethod
    def serialize_date(value: date) -> str:
        return f"'{value.isoformat()}'::date"

    @staticmethod
    def serialize_datetime(value: datetime) -> str:
        return f"'{value.isoformat()}'"

    def serialize_sequence(self, value: Iterable) -> str:
        items = ', '.join(self.serialize_value(item) for item in value)
        return f'array[{items}]'


__all__ = ('PostgresSerializer',)
