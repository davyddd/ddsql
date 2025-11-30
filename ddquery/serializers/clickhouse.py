from datetime import date, datetime
from typing import Iterable
from uuid import UUID

from ddquery.serializers import BaseSerializer


class ClickhouseSerializer(BaseSerializer):
    @staticmethod
    def serialize_uuid(value: UUID) -> str:
        return f"toUUID('{value}')"

    @staticmethod
    def serialize_date(value: date) -> str:
        return f"toDate('{value.isoformat()}')"

    @staticmethod
    def serialize_datetime(value: datetime) -> str:
        return f"parseDateTimeBestEffort('{value.isoformat()}')"

    def serialize_sequence(self, value: Iterable) -> str:
        items = ', '.join(self.serialize_value(item) for item in value)
        return f'[{items}]'


__all__ = ('ClickhouseSerializer',)
