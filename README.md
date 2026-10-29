# ddsql

[![pypi](https://img.shields.io/pypi/v/ddsql.svg)](https://pypi.python.org/pypi/ddsql)
[![downloads](https://static.pepy.tech/badge/ddsql/month)](https://pepy.tech/project/ddsql)
[![versions](https://img.shields.io/pypi/pyversions/ddsql.svg)](https://github.com/davyddd/ddsql)
[![codecov](https://codecov.io/gh/davyddd/ddsql/branch/main/graph/badge.svg)](https://app.codecov.io/github/davyddd/ddsql)
[![license](https://img.shields.io/github/license/davyddd/ddsql.svg)](https://github.com/davyddd/ddsql/blob/main/LICENSE)

SQL queries from Jinja2 templates with typed results and Postgres and ClickHouse adapters

## Installation

Install the library using pip:
```bash
pip install ddsql
```

## Development

The project runs entirely in Docker. Requires Docker and [Fabric](https://www.fabfile.org/) on the host:

```bash
fab build      # build the dev image
fab tests      # run pytest
fab linters    # run ruff (with --fix), ty and complexipy
fab shell      # IPython inside the container
fab bash       # bash inside the container
```

This project was generated from [dd-lib-stub](https://github.com/davyddd/dd-lib-stub);
run `uvx copier update` to pull in template updates.

## Compatibility

Python 3.11 to 3.15. What changed in each release, breaking changes included,
is in the [GitHub releases](https://github.com/davyddd/ddsql/releases).

<!-- The sections below are the library's own; copier update leaves them alone -->

Depends on `jinja2>=3,<4` and `ddutils>=0.3.1,<0.5.0`; the database drivers are the project's, ddsql renders SQL
and wraps rows while an adapter runs the query. The tests need no database.

## Serializer

The serializer converts Python types to their SQL representations. 
You can use one of the built-in serializers (`PostgresSerializer`, `ClickhouseSerializer`) 
or create your own by inheriting from `BaseSerializer`.

**Serialization Table**

| Python Type          | Base                    | PostgreSQL                         | ClickHouse                                            |
|----------------------|-------------------------|------------------------------------|-------------------------------------------------------|
| `None`               | `NULL`                  | `NULL`                             | `NULL`                                                |
| `bool`               | `true`/`false`          | `true`/`false`                     | `true`/`false`                                        |
| `int`                | `123`                   | `123`                              | `123`                                                 |
| `float`/`Decimal`    | `45.67`                 | `45.67`                            | `45.67`                                               |
| `str`                | `'value'`               | `'value'`                          | `'value'`                                             |
| `UUID`               | `'550e8400-...'`        | `'550e8400-...'::uuid`             | `toUUID('550e8400-...')`                              |
| `datetime`           | `'2025-01-01T12:00:00'` | `'2025-01-01T12:00:00'::timestamp` | `parseDateTime64BestEffort('2025-01-01T12:00:00', 6)` |
| `date`               | `'2025-01-01'`          | `'2025-01-01'::date`               | `toDate('2025-01-01')`                                |
| `list`/`tuple`/`set` | `(item1, item2, ...)`   | `(item1, item2, ...)`              | `(item1, item2, ...)`                                 |

An `Enum` member is serialized by its value: `Kind.ADMIN` of a `class Kind(str, Enum)` renders as `'admin'`,
a plain `Enum` holding a `datetime` as that `datetime`. A subclass is matched as its base type
(a `ProfileId(UUID)` as a `UUID`, a `pendulum.DateTime` as a `datetime`). The collection row covers any
`Collection` that is not a mapping, a `str` or bytes, with the items serialized recursively; an empty collection
renders as `()`, which is not valid after `IN`, so guard it in the template. `bytes`, `bytearray`, `dict` and other
mappings, `time` and `timedelta` are not serialized: like any other type missing from the table they go to
`serialize_other_object`, which raises `NotImplementedError` unless overridden. Numbers render with `str()`, so
`float('inf')` and `float('nan')` produce `inf` and `nan`, which no database accepts.

String values are escaped according to the dialect rules, so quotes, backslashes 
and control characters cannot break the query:

- `BaseSerializer` doubles single quotes (`O'Brien` → `'O''Brien'`), as defined by the SQL standard.
- `ClickhouseSerializer` escapes backslashes, single quotes and all control characters 
  with backslash sequences (`O'Brien` → `'O\'Brien'`, newline → `\n`, other control characters → `\xHH`).
- `PostgresSerializer` doubles single quotes; strings containing backslashes or control 
  characters are emitted using the escape string syntax (`C:\dir` → `E'C:\\dir'`), which is 
  interpreted the same way regardless of the `standard_conforming_strings` server setting. 
  A NUL (`0x00`) character raises `ValueError`, since PostgreSQL cannot store it in text values.

The serialized literal is always a single printable line. 

`datetime` values keep their microseconds and UTC offset:

- `ClickhouseSerializer` renders `parseDateTime64BestEffort('...', 6)`, which yields a `DateTime64(6)` 
  literal; a timezone-aware value is converted according to its offset, a naive value is interpreted 
  in the server time zone. Inserting such a literal into a `DateTime` column silently truncates it 
  to seconds, and comparisons with `DateTime` columns work as expected.
- `PostgresSerializer` renders a timezone-aware value as `'...+03:00'::timestamptz`, so its offset 
  is honoured; a naive value is rendered as `'...'::timestamp`, as before.

To customize escaping in your own serializer, override the `escape_string` method.

If you need to serialize a type not listed in the table, override the `serialize_other_object` method in your serializer:

```python
from ddsql.serializers import BaseSerializer


class CustomSerializer(BaseSerializer):
    def serialize_other_object(self, value):
        if isinstance(value, CustomType):
            return ...
        ...
```

To serialize values in SQL templates, wrap parameters with `serialize_value`:

```sql
SELECT * 
FROM users
WHERE 
    name = {{ serialize_value(name) }}
    AND created_at > {{ serialize_value(created_at) }}
```

To add custom functions to templates, override the `template_functions` property. They are installed as Jinja
globals, so they are available inside macros and included templates as well:

```python
from ddsql.serializers import BaseSerializer


class CustomSerializer(BaseSerializer):
    @property
    def template_functions(self):
        return {
            **super().template_functions,
            'some_function': ...,
        }
```

## Connections

Connection routing (`ConnectionManagerFactory`, `ConnectionManager`) lives in
[ddutils](https://github.com/davyddd/ddutils#connections) since it is not specific to SQL: a `ScopedRegistry` per
alias, a factory that opens a connection manager on the chosen registry, like Django's `using`. An adapter runs its
query inside `factory(alias=self.alias)`; see "Choosing the database" below.

## Adapter

`Adapter` encapsulates database interactions. To create an adapter, inherit from the `Adapter` base class
and define two required elements:
- **serializer** – an instance of a serializer for converting Python types to SQL representations;
- **_execute** method – the database-specific query execution logic, returning the rows as a sequence of dicts.

An adapter is created by `SQLBase` for one execution with the `SQL` object as `sql`; `get_query()` renders the
template with the parameters and the serializer's functions, `execute()` runs `_execute()` and wraps the rows
into a `Result`, `alias` is the connection chosen with `using()`.

```python
from collections.abc import Sequence
from typing import Any

from ddutils.connections import ConnectionManagerFactory
from sqlalchemy import text

from ddsql.adapter import Adapter
from ddsql.serializers import PostgresSerializer

# a unit of work over the session registries, see ddutils' Connections
atomic = ConnectionManagerFactory(session_registries, default=PostgresDB.PRIMARY, connection_manager_class=Atomic)


class PostgresAdapter(Adapter):
    serializer = PostgresSerializer()

    async def _execute(self) -> Sequence[dict[str, Any]]:
        async with atomic(alias=self.alias) as session:
            query = await self.get_query()  # the rendered SQL query
            result = await session.execute(text(query))
            return [dict(zip(result.keys(), row)) for row in result.fetchall()]
```

Intermediate adapter classes without `_execute` are abstract and need no `serializer`; a concrete adapter
without one raises `NotImplementedError` at class definition.

### Choosing the database

`Adapter.using(alias)` picks the connection alias right before executing, like Django's `using`. `_execute`
reads `self.alias` (`None` means the default) and passes it to whatever opens the connection, as in the example above:

```python
await SQL(query).postgres.execute()                               # default connection
await SQL(query).postgres.using(PostgresDB.REPLICA).execute()
```

`SQL(query).postgres` creates a new adapter on every access, so `using()` and `execute()` must be chained in one
expression: an alias set on one adapter instance is not seen by the next.

## SQLBase

`SQLBase` is configured once per project and defines which adapters are available for query execution. 
It serves as the central point that connects queries with database adapters.

Create a subclass with one or more adapters; a subclass without any, inherited ones included, raises
`NotImplementedError` at class definition:

```python
from ddsql.sqlbase import SQLBase
from ddsql.adapter import AdapterDescriptor


class SQL(SQLBase):
    postgres: PostgresAdapter = AdapterDescriptor(PostgresAdapter)
    clickhouse: ClickhouseAdapter = AdapterDescriptor(ClickhouseAdapter)
```

Execution example:

```python
from ddsql.query import Query


query = Query(...)
result = await SQL(query=query).with_params(email='test@test.test', is_deleted=False).postgres.execute()
```

`with_params` merges into the object's parameters and returns the same object, so an `SQL` instance is one
execution: build a new `SQL(query)` for every query instead of keeping one around.

## Query

`Query` knows where to get the template from and how to render a SQL query. 
It also handles result deserialization via the `build_result` method, 
which wraps raw database rows into the specified model (called internally by `Adapter.execute`).

Required parameters:
- **model** – any callable that takes the columns as keyword arguments and returns a row object: a dataclass, a
  pydantic model, a `NamedTuple`;
- **text** or **path** – the SQL template source (inline string or a `pathlib.Path` to a file). An empty `text`
  counts as not given.

`Query[User]` and `Result[User]` are generic in the model, so `result.get()` is typed as `User | None`.
The Jinja environment is async with `trim_blocks`, `lstrip_blocks` and `keep_trailing_newline`; the rendered
SQL has every line stripped of leading and trailing whitespace.

### Inline Template (text)

```python
from ddsql.query import Query


query = Query(
    model=User,
    text='SELECT user_id, name FROM users WHERE user_id = {{ serialize_value(user_id) }}'
)
```

### File Template (path)

Pass the path to the SQL file as `Path`. The file is checked at construction time, so a wrong path fails
on import rather than on the first query:

```python
from pathlib import Path

from ddsql.query import Query

SQL_TEMPLATES_DIR = Path(__file__).parent / 'templates' / 'sql'

query = Query(
    model=User,
    path=SQL_TEMPLATES_DIR / 'users' / 'get_by_id.sql',
)
```

`{% include %}` and `{% import %}` inside the template resolve relative to the template's directory.

### Result

The result of query execution is a `Result` object that wraps the data into the specified model:
- `get()` – returns the first row as a model instance, or `None` if empty;
- `get_list()` – returns all rows as a tuple of model instances;
- `rows` – attribute for accessing raw data.

## Complete Example

```python
from dataclasses import dataclass
from datetime import datetime

from ddsql.adapter import Adapter, AdapterDescriptor
from ddsql.query import Query
from ddsql.serializers import PostgresSerializer
from ddsql.sqlbase import SQLBase


class PostgresAdapter(Adapter):
    serializer = PostgresSerializer()

    async def _execute(self):
        ...


class SQL(SQLBase):
    postgres: PostgresAdapter = AdapterDescriptor(PostgresAdapter)


@dataclass
class User:
    user_id: int
    name: str
    email: str | None
    created_at: datetime
    is_deleted: bool


query = Query(
    model=User,
    text='''
        SELECT *
        FROM users
        WHERE 
            created_at > {{ serialize_value(created_after) }}
        LIMIT {{ limit }}
    '''
)


async def get_users():
    result = await (
        SQL(query=query)
        .with_params(created_after=datetime(2025, 1, 1))
        .with_params(limit=10)
        .postgres
        .execute()
    )
    return result.get_list()
```
