from dataclasses import dataclass

from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.services.api_client_v2.mpt_api_client import AsyncMPTClient
from mpt_extension_sdk.services.mpt_api_service.base import BaseService


class FakeModel(BaseModel):
    @classmethod
    def from_payload(cls, payload):
        return {"payload": payload}


class FakeService(BaseService[FakeModel]):
    """Fake service exposing base pagination for tests."""


@dataclass
class FakePagination:
    limit: int
    offset: int
    total: int


@dataclass
class FakeMeta:
    pagination: FakePagination


class FakePage:
    def __init__(self, elements, meta=None):
        self.elements = elements
        self.meta = meta

    def __iter__(self):
        return iter(self.elements)

    def __len__(self):
        return len(self.elements)


async def test_paginate_fetches_page(mocker):
    meta = FakeMeta(FakePagination(limit=2, offset=4, total=10))
    collection = mocker.Mock(spec=["fetch_page"])
    collection.fetch_page = mocker.AsyncMock(return_value=FakePage(["one", "two"], meta=meta))
    mocker.patch.object(
        FakeModel,
        "from_payload",
        autospec=True,
        side_effect=[{"payload": "one"}, {"payload": "two"}],
    )
    service = FakeService(mocker.Mock(spec=AsyncMPTClient))

    result = await service._paginate(collection, FakeModel, offset=4, limit=2)

    collection.fetch_page.assert_awaited_once_with(offset=4, limit=2)
    assert result.offset == 4
    assert result.limit == 2
    assert result.resources == [{"payload": "one"}, {"payload": "two"}]
    assert result.total == 10


async def test_paginate_falls_back_when_meta_missing(mocker):
    collection = mocker.Mock(spec=["fetch_page"])
    collection.fetch_page = mocker.AsyncMock(return_value=FakePage(["one", "two"], meta=None))
    mocker.patch.object(
        FakeModel,
        "from_payload",
        autospec=True,
        side_effect=[{"payload": "one"}, {"payload": "two"}],
    )
    service = FakeService(mocker.Mock(spec=AsyncMPTClient))

    result = await service._paginate(collection, FakeModel, offset=4, limit=2)

    collection.fetch_page.assert_awaited_once_with(offset=4, limit=2)
    assert result.offset == 4
    assert result.limit == 2
    assert result.resources == [{"payload": "one"}, {"payload": "two"}]
    assert result.total == 6
