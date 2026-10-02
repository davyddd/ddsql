from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from ddutils.annotation_helpers import is_subclass

from ddsql.serializers import BaseSerializer

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddsql.query import Result
    from ddsql.sqlbase import SQLBase


class Adapter(ABC):
    serializer: BaseSerializer

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
    async def _execute(self) -> Sequence[dict[str, Any]]: ...


AdapterT = TypeVar('AdapterT', bound=Adapter)


class AdapterDescriptor(Generic[AdapterT]):
    adapter_class: type[AdapterT]

    def __init__(self, adapter_class: type[AdapterT]):
        self.adapter_class = adapter_class

    @overload
    def __get__(self, sql: None, sql_class: type[SQLBase]) -> AdapterDescriptor[AdapterT]: ...

    @overload
    def __get__(self, sql: SQLBase, sql_class: type[SQLBase] | None = None) -> AdapterT: ...

    def __get__(self, sql: SQLBase | None, sql_class: type[SQLBase] | None = None) -> AdapterT | AdapterDescriptor[AdapterT]:
        # accessed on the class, like `SQL.postgres`: return the descriptor itself, as `property` does
        if sql is None:
            return self
        return self.adapter_class(sql)


__all__ = ('Adapter', 'AdapterDescriptor')
