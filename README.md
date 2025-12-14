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

## Serializer

The serializer converts Python types to their SQL representations. 
You can use one of the built-in serializers (`PostgresSerializer`, `ClickhouseSerializer`) 
or create your own by inheriting from `BaseSerializer`.

**Serialization Table**

| Python Type          | Base                     | PostgreSQL                          | ClickHouse                                        |
|----------------------|--------------------------|-------------------------------------|---------------------------------------------------|
| `None`               | `NULL`                   | `NULL`                              | `NULL`                                            |
| `bool`               | `true`/`false`           | `true`/`false`                      | `true`/`false`                                    |
| `int`                | `123`                    | `123`                               | `123`                                             |
| `float`/`Decimal`    | `45.67`                  | `45.67`                             | `45.67`                                           |
| `str`                | `'value'`                | `'value'`                           | `'value'`                                         |
| `UUID`               | `'550e8400-...'`         | `'550e8400-...'::uuid`              | `toUUID('550e8400-...')`                          |
| `datetime`           | `'2025-01-01T12:00:00'`  | `'2025-01-01T12:00:00'::timestamp`  | `parseDateTimeBestEffort('2025-01-01T12:00:00')`  |
| `date`               | `'2025-01-01'`           | `'2025-01-01'::date`                | `toDate('2025-01-01')`                            |
| `list`/`tuple`/`set` | `(item1, item2, ...)`    | `(item1, item2, ...)`               | `(item1, item2, ...)`                             |

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

## Adapter

`Adapter` encapsulates database interactions. To create an adapter, inherit from the `Adapter` base class 
and define two required elements:
- **serializer** – an instance of a serializer for converting Python types to SQL representations;
- **_execute** method – the database-specific query execution logic.

```python
from ddsql.adapter import Adapter
from ddsql.serializers import PostgresSerializer


class PostgresAdapter(Adapter):
    serializer = PostgresSerializer()

    async def _execute(self) -> Sequence[Dict[str, Any]]:
        query = await self.get_query()  # get the rendered SQL query
        async with Atomic() as postgres_session:
            result = await postgres_session.execute(text(query))
            return [dict(zip(result.keys(), row)) for row in result.fetchall()]
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
- **text** or **path** – the SQL template source.

### Inline Template (text)

```python
from ddsql.query import Query


query = Query(
    model=User,
    text='SELECT user_id, name FROM users WHERE user_id = {{ serialize_value(user_id) }}'
)
```

### File Template (path)

For file-based templates, set the `SQL_TEMPLATES_DIR` environment variable to the directory containing your SQL files:

```bash
export SQL_TEMPLATES_DIR=/app/src/templates/sql/
```

Then use a relative path:

```python
from ddsql.query import Query


# Loads template from /app/src/templates/sql/users/get_by_id.sql
query = Query(
    model=User, 
    path='users/get_by_id.sql'
)
```

### Result

The result of query execution is a `Result` object that wraps the data into the specified model:
- `get()` – returns the first row as a model instance, or `None` if empty;
- `get_list()` – returns all rows as a tuple of model instances;
- `rows` – attribute for accessing raw data.

## Complete Example

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ddsql.query import Query
from ddsql.sqlbase import SQLBase
from ddsql.adapter import Adapter, AdapterDescriptor
from ddsql.serializers import PostgresSerializer


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
    email: Optional[str]
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