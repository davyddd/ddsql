import os
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Sequence, Type, TypeVar

from jinja2 import Environment, FileSystemLoader, Template

SQL_TEMPLATES_DIR = os.getenv('SQL_TEMPLATES_DIR')


DataT = TypeVar('DataT')


class Result(Generic[DataT]):
    rows: Sequence[dict[str, Any]]
    model: Type[DataT]

    def __init__(self, rows: Sequence[dict[str, Any]], model: Type[DataT]):
        self.rows = rows
        self.model = model

    def get(self) -> Optional[DataT]:
        if not self.rows:
            return None
        return self.model(**self.rows[0])

    def get_list(self) -> List[DataT]:
        return [self.model(**row) for row in self.rows]


class Query(Generic[DataT]):
    model: Type[DataT]
    template: Template

    def __init__(
        self, model: Type[DataT], text: Optional[str] = None, path: Optional[str] = None, envs: Optional[Dict[str, Any]] = None
    ):
        self.model = model

        self.template = self.get_template(text, path)
        self.update_globals(envs)

    @staticmethod
    def get_template(text: Optional[str] = None, path: Optional[str] = None) -> Template:
        if text:
            file_system_loader = FileSystemLoader(Path('.'))
            method = 'from_string'
            query = text
        elif path:
            if SQL_TEMPLATES_DIR is None:
                raise ValueError(
                    'SQL Templates dir is not defined. Make sure the SQL_TEMPLATES_DIR environment variable is set correctly.'
                )
            file_system_loader = FileSystemLoader(Path(SQL_TEMPLATES_DIR))
            method = 'get_template'
            query = path
        else:
            raise ValueError('One of `text` or `path` must be specified')

        environment = Environment(
            loader=file_system_loader, trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True, enable_async=True
        )

        return getattr(environment, method)(query)

    def update_globals(self, envs: Optional[Dict[str, Any]] = None):
        if envs:
            self.template.environment.globals.update(envs)

    @staticmethod
    def format_sql(sql: str) -> str:
        strings = sql.split('\n')
        return '\n'.join([string.strip() for string in strings])

    async def render_template(self, params: Dict[str, Any], template_functions: Dict[str, Any]) -> str:
        self.update_globals(template_functions)

        rendered_template = await self.template.render_async(**params)
        return self.format_sql(rendered_template)

    def build_result(self, rows: Sequence[dict[str, Any]]) -> Result[DataT]:
        return Result(rows=rows, model=self.model)


__all__ = ('Result', 'Query')
