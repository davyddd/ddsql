from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any, TypeVar

from ddutils.class_helpers import classproperty

from ddsql.adapter import AdapterDescriptor

if TYPE_CHECKING:
    from ddsql.query import Query

T = TypeVar('T', bound='SQLBase')


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
    params: dict[str, Any]

    def __init_subclass__(cls, **kwargs):
        if not cls.has_adapters:
            raise NotImplementedError('Subclasses must define at least one adapter')

    @classproperty
    def has_adapters(cls: type[SQLBase]) -> bool:
        # Descriptors are looked up in the class dictionaries along the MRO, so inherited adapters count
        # and no adapter gets instantiated just for the check
        return any(isinstance(value, AdapterDescriptor) for klass in cls.__mro__ for value in vars(klass).values())

    def __init__(self, query: Query) -> None:
        self.query = query
        self.params = {}

    def with_params(self: T, **params: Any) -> T:
        self.params = {**self.params, **params}
        return self


__all__ = ('SQLBase',)
