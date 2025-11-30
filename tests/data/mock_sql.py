from collections.abc import Sequence
from typing import Any, Dict

from ddquery.adapter import Adapter, AdapterDescriptor
from ddquery.serializers import BaseSerializer
from ddquery.sqlbase import SQLBase


class MockAdapter(Adapter):
    serializer = BaseSerializer()

    async def _execute(self) -> Sequence[Dict[str, Any]]:
        return [{'user_id': 1, 'name': 'Test User', 'email': None}]


class MockSQL(SQLBase):
    mock_adapter: MockAdapter = AdapterDescriptor[MockAdapter](MockAdapter)  # type: ignore
