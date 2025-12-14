from datetime import date, datetime
from uuid import UUID

from ddsql.serializers import BaseSerializer


class PostgresSerializer(BaseSerializer):
    @staticmethod
    def serialize_uuid(value: UUID) -> str:
        return f"'{value}'::uuid"

    @staticmethod
    def serialize_datetime(value: datetime) -> str:
        return f"'{value.isoformat()}'::timestamp"

    @staticmethod
    def serialize_date(value: date) -> str:
        return f"'{value.isoformat()}'::date"


__all__ = ('PostgresSerializer',)
