from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Generic, Optional, Sequence, Type, TypeVar

from ddutils.annotation_helpers import is_subclass

from ddsql.serializers import BaseSerializer

if TYPE_CHECKING:
    from ddsql.query import Result
    from ddsql.sqlbase import SQLBase


class Adapter(ABC):
    serializer: BaseSerializer

    @classmethod
    def __init_subclass__(cls, **kwargs):
        serializer = getattr(cls, 'serializer', None)
        serializer_class = getattr(serializer, '__class__', None)
        if not is_subclass(serializer_class, BaseSerializer):
            raise NotImplementedError(
                'Subclass of Adapter must define a valid serializer attribute that is a subclass of Serializer'
            )

    def __init__(self, sql: SQLBase) -> None:
        self.sql = sql

    async def get_query(self) -> str:
        return await self.sql.query.render_template(
            params=self.sql.params, template_functions=self.serializer.template_functions
        )

    async def execute(self) -> Result:
        return self.sql.query.build_result(await self._execute())

    @abstractmethod
    async def _execute(self) -> Sequence[Dict[str, Any]]:  # noqa: UP006
        ...


AdapterT = TypeVar('AdapterT', bound=Adapter)


class AdapterDescriptor(Generic[AdapterT]):
    adapter_class: Type[AdapterT]  # noqa: UP006

    def __init__(self, adapter_class: Type[AdapterT]):  # noqa: UP006
        self.adapter_class = adapter_class

    def __get__(self, sql: SQLBase, sql_class: Optional[Type[SQLBase]] = None) -> AdapterT:  # noqa: UP006, UP007
        return self.adapter_class(sql)


__all__ = ('Adapter', 'AdapterDescriptor')
