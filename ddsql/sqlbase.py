from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any, Dict

from ddutils.annotation_helpers import is_subclass
from ddutils.class_helpers import classproperty

from ddsql.adapter import Adapter

if TYPE_CHECKING:
    from ddsql.query import Query


class SQLBase(ABC):
    """
    Abstract base class for SQL query execution with adapter-based database connections.

    This class provides a foundation for executing SQL queries against different database backends
    using adapters. It handles query preparation, parameter management, and adapter selection.

    Subclasses must define at least one adapter as a class attribute.

    Attributes:
        query: The SQL query to execute, either as a Query object or raw SQL string
        params: Dictionary of parameters to be used in the query
    """

    query: Query
    params: Dict[str, Any]

    @classmethod
    def __init_subclass__(cls, **kwargs):
        if not cls.has_adapters:
            raise NotImplementedError('Subclasses must define at least one adapter')

    @classproperty
    def has_adapters(cls) -> bool:
        for field in cls.__annotations__:
            adapter = getattr(cls, field, None)
            adapter_class = getattr(adapter, '__class__', None)
            if adapter_class and is_subclass(adapter_class, Adapter):
                return True

        return False

    def __init__(self, query: Query) -> None:
        self.query = query
        self.params = {}

    def with_params(self, **params: Any) -> SQLBase:
        self.params = {**self.params, **params}
        return self


__all__ = ('SQLBase',)
