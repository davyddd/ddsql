import re
from datetime import date, datetime
from uuid import UUID

from ddsql.serializers import BaseSerializer

# Characters a regular literal cannot represent reliably: control characters have no escape
# sequences there, and a backslash changes meaning when standard_conforming_strings is off.
# Strings containing them are serialized with the escape string syntax (E'...') instead.
_ESCAPE_SYNTAX_REQUIRED = re.compile(r'[\\\x00-\x1F\x7F]')


def _build_escape_translation() -> dict[int, str]:
    # https://www.postgresql.org/docs/current/sql-syntax-lexical.html#SQL-SYNTAX-STRINGS-ESCAPE
    translation = {
        ord('\\'): '\\\\',
        ord("'"): "''",
        ord('\b'): '\\b',
        ord('\t'): '\\t',
        ord('\n'): '\\n',
        ord('\f'): '\\f',
        ord('\r'): '\\r',
    }
    # control characters without a named escape sequence
    for code in range(0x20):
        translation.setdefault(code, f'\\x{code:02X}')
    translation[0x7F] = '\\x7F'
    return translation


_ESCAPE_TRANSLATION = _build_escape_translation()


class PostgresSerializer(BaseSerializer):
    @staticmethod
    def escape_string(value: str) -> str:
        # PostgreSQL follows the SQL standard: a single quote is escaped by doubling it
        return value.replace("'", "''")

    @classmethod
    def serialize_string(cls, value: str) -> str:
        if '\x00' in value:
            raise ValueError('PostgreSQL does not support the NUL (0x00) character in string values')
        if _ESCAPE_SYNTAX_REQUIRED.search(value):
            return f"E'{value.translate(_ESCAPE_TRANSLATION)}'"
        return f"'{cls.escape_string(value)}'"

    @classmethod
    def serialize_uuid(cls, value: UUID) -> str:
        return f"'{cls.escape_string(str(value))}'::uuid"

    @classmethod
    def serialize_datetime(cls, value: datetime) -> str:
        # `timestamp` ignores the UTC offset of the literal, so a timezone-aware value
        # is rendered as `timestamptz` to keep its offset; naive values are left as-is
        cast = 'timestamptz' if value.tzinfo is not None else 'timestamp'
        return f"'{cls.escape_string(value.isoformat())}'::{cast}"

    @classmethod
    def serialize_date(cls, value: date) -> str:
        return f"'{cls.escape_string(value.isoformat())}'::date"


__all__ = ('PostgresSerializer',)
