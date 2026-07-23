from datetime import date, datetime
from typing import Dict
from uuid import UUID

from ddsql.serializers import BaseSerializer


def _build_escape_translation() -> Dict[int, str]:
    # https://clickhouse.com/docs/en/sql-reference/syntax#string
    translation = {
        ord('\\'): '\\\\',
        ord("'"): "\\'",
        ord('\0'): '\\0',
        ord('\a'): '\\a',
        ord('\b'): '\\b',
        ord('\t'): '\\t',
        ord('\n'): '\\n',
        ord('\v'): '\\v',
        ord('\f'): '\\f',
        ord('\r'): '\\r',
    }
    # control characters without a named escape sequence
    for code in range(0x20):
        translation.setdefault(code, f'\\x{code:02X}')
    translation[0x7F] = '\\x7F'
    return translation


_ESCAPE_TRANSLATION = _build_escape_translation()


class ClickhouseSerializer(BaseSerializer):
    @staticmethod
    def escape_string(value: str) -> str:
        return value.translate(_ESCAPE_TRANSLATION)

    @classmethod
    def serialize_uuid(cls, value: UUID) -> str:
        return f"toUUID('{cls.escape_string(str(value))}')"

    @classmethod
    def serialize_datetime(cls, value: datetime) -> str:
        return f"parseDateTimeBestEffort('{cls.escape_string(value.isoformat())}')"

    @classmethod
    def serialize_date(cls, value: date) -> str:
        return f"toDate('{cls.escape_string(value.isoformat())}')"


__all__ = ('ClickhouseSerializer',)
