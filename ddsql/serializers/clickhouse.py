from datetime import date, datetime
from uuid import UUID

from ddsql.serializers import BaseSerializer


class ClickhouseSerializer(BaseSerializer):
    @staticmethod
    def serialize_uuid(value: UUID) -> str:
        return f"toUUID('{value}')"

    @staticmethod
    def serialize_datetime(value: datetime) -> str:
        return f"parseDateTimeBestEffort('{value.isoformat()}')"

    @staticmethod
    def serialize_date(value: date) -> str:
        return f"toDate('{value.isoformat()}')"


__all__ = ('ClickhouseSerializer',)
