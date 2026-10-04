# DDSQL

[![pypi](https://img.shields.io/pypi/v/ddsql.svg)](https://pypi.python.org/pypi/ddsql)
[![downloads](https://static.pepy.tech/badge/ddsql/month)](https://pepy.tech/project/ddsql)
[![versions](https://img.shields.io/pypi/pyversions/ddsql.svg)](https://github.com/davyddd/ddsql)
[![codecov](https://codecov.io/gh/davyddd/ddsql/branch/main/graph/badge.svg)](https://app.codecov.io/github/davyddd/ddsql)
[![license](https://img.shields.io/github/license/davyddd/ddsql.svg)](https://github.com/davyddd/ddsql/blob/main/LICENSE)

**DDSQL** is a Python library for building SQL queries with Jinja2 template rendering and database adapter support.
Query results are automatically deserialized into typed models.

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
run `copier update` to pull in template updates.

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

To add custom functions to templates, override the `template_functions` property:

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

`ddsql.connections` sits between a `ScopedRegistry` (from [ddutils](https://github.com/davyddd/ddutils)) and
the code that runs queries. A registry holds one connection per scope: a pooled client per process, a session
per task. The connections module adds two things on top:

- `ConnectionManagerFactory(registries, default, connection_manager_class=ConnectionManager)` resolves a
  connection alias to its registry, like Django's `using`. Calling it opens a connection manager on the
  chosen registry; `registry(using)` returns the registry itself.
- `ConnectionManager(registry)` is the default connection manager: an async context manager that hands out
  the connection of the registry's current scope and releases nothing on exit. Enough for clients that are
  pools themselves, such as ClickHouse.

Databases with transactions pass their own `connection_manager_class`: a unit of work that begins, commits
or rolls back and closes the session on exit. It depends on the driver, so it lives in the project.

```python
import os
from enum import Enum

from ddutils.scoped_registry import ScopedRegistry

from ddsql.connections import ConnectionManagerFactory


class ClickhouseDB(str, Enum):
    PRIMARY = 'primary'


client_registries = {
    db: ScopedRegistry(create_func=make_client_for(db), scope_func=os.getpid, destructor_method_name='close')
    for db in ClickhouseDB
}
clickhouse = ConnectionManagerFactory(client_registries, default=ClickhouseDB.PRIMARY)


async with clickhouse() as client:
    result = await client.query(sql)


# a transactional database: `Atomic` is your unit of work over `registry.scope()`
atomic = ConnectionManagerFactory(session_registries, default=PostgresDB.PRIMARY, connection_manager_class=Atomic)


async with atomic(using=PostgresDB.REPLICA) as session:
    ...
```

## Adapter

`Adapter` encapsulates database interactions. To create an adapter, inherit from the `Adapter` base class
and define two required elements:
- **serializer** – an instance of a serializer for converting Python types to SQL representations;
- **_execute** method – the database-specific query execution logic.

```python
from collections.abc import Sequence
from typing import Any

from sqlalchemy import text

from ddsql.adapter import Adapter
from ddsql.serializers import PostgresSerializer


class PostgresAdapter(Adapter):
    serializer = PostgresSerializer()

    async def _execute(self) -> Sequence[dict[str, Any]]:
        async with atomic(using=self.db) as session:
            query = await self.get_query()  # the rendered SQL query
            result = await session.execute(text(query))
            return [dict(zip(result.keys(), row)) for row in result.fetchall()]
```

Intermediate adapter classes without `_execute` are abstract and need no `serializer`; only concrete
adapters are validated.

### Choosing the database

`Adapter.using(db)` picks the database right before executing, like Django's `using`. `_execute` reads
`self.db` (`None` means the default) and passes it to whatever opens the connection, as in the example above:

```python
await SQL(query).postgres.execute()                               # default connection
await SQL(query).postgres.using(PostgresDB.REPLICA).execute()
```

## SQLBase

`SQLBase` is configured once per project and defines which adapters are available for query execution. 
It serves as the central point that connects queries with database adapters.

Create a subclass with one or more adapters:

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

## Query

`Query` knows where to get the template from and how to render a SQL query. 
It also handles result deserialization via the `build_result` method, 
which wraps raw database rows into the specified model (called internally by `Adapter.execute`).

Required parameters:
- **model** – a declarative class (e.g., dataclass) describing the output result structure;
- **text** or **path** – the SQL template source (inline string or path to a file).

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