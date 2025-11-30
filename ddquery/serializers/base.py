from collections.abc import Callable, Collection, Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Union
from uuid import UUID


class BaseSerializer:
    @property
    def template_functions(self) -> Dict[str, Callable[[Any], str]]:
        return {'serialize_value': self.serialize_value}

    def serialize_value(self, value: Any) -> str:
        if value is None:
            return self.serialize_none(value)
        elif isinstance(value, bool):
            return self.serialize_bool(value)
        elif isinstance(value, (int, float, Decimal)):
            return self.serialize_number(value)
        elif isinstance(value, str):
            return self.serialize_string(value)
        elif isinstance(value, UUID):
            return self.serialize_uuid(value)
        elif isinstance(value, datetime):
            return self.serialize_datetime(value)
        elif isinstance(value, date):
            # the check for date must come after datetime,
            # because a datetime instance can also be identified as a date
            return self.serialize_date(value)
        elif isinstance(value, Collection) and not isinstance(value, Mapping):
            return self.serialize_collection(value)
        else:
            return self.serialize_other_object(value)

    @staticmethod
    def serialize_none(value) -> str:  # noqa: ARG004
        return 'NULL'

    @staticmethod
    def serialize_bool(value: bool) -> str:
        return f'{value}'.lower()

    @staticmethod
    def serialize_number(value: Union[int, float, Decimal]) -> str:
        return f'{value}'

    @staticmethod
    def serialize_string(value: str) -> str:
        return f"'{value}'"

    @staticmethod
    def serialize_uuid(value: UUID) -> str:
        return f"'{value}'"

    @staticmethod
    def serialize_datetime(value: datetime) -> str:
        return f"'{value.isoformat()}'"

    @staticmethod
    def serialize_date(value: date) -> str:
        return f"'{value.isoformat()}'"

    def serialize_collection(self, value: Collection) -> str:
        items = ', '.join(self.serialize_value(item) for item in value)
        return f'({items})'

    def serialize_other_object(self, value: Any) -> str:
        raise NotImplementedError()


__all__ = ('BaseSerializer',)
