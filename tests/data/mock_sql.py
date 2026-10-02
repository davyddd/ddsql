from collections.abc import Sequence
from typing import Any

from ddsql.adapter import Adapter, AdapterDescriptor
from ddsql.serializers import BaseSerializer
from ddsql.sqlbase import SQLBase


class MockAdapter(Adapter):
    serializer = BaseSerializer()

    async def _execute(self) -> Sequence[dict[str, Any]]:
        return [{'user_id': 1, 'name': 'Test User', 'email': None}]


class MockSQL(SQLBase):
    mock_adapter: MockAdapter = AdapterDescriptor[MockAdapter](MockAdapter)  # type: ignore
