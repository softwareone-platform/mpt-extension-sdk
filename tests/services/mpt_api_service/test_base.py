from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.services.api_client_v2.mpt_api_client import AsyncMPTClient
from mpt_extension_sdk.services.mpt_api_service.base import BaseService


class FakeModel(BaseModel):
    @classmethod
    def from_payload(cls, payload):
        return {"payload": payload}


class FakeService(BaseService[FakeModel]):
    async def get_all(self, collection, batch_size=100):
        return await self._iterate_all(collection, FakeModel, batch_size=batch_size)


class FakeCollection:
    def __init__(self, elements):
        self.elements = elements
        self.batch_sizes = []

    async def iterate(self, *, batch_size):
        self.batch_sizes.append(batch_size)
        for element in self.elements:
            yield element


async def test_get_all_collects_models(mocker):
    collection = FakeCollection(["one", "two"])
    mocker.patch.object(
        FakeModel,
        "from_payload",
        autospec=True,
        side_effect=[{"payload": "one"}, {"payload": "two"}],
    )
    service = FakeService(mocker.Mock(spec=AsyncMPTClient))

    result = await service.get_all(collection)

    assert result == [{"payload": "one"}, {"payload": "two"}]


async def test_get_all_passes_batch_size(mocker):
    collection = FakeCollection(["x"])
    mocker.patch.object(FakeModel, "from_payload", autospec=True, return_value={"payload": "x"})
    service = FakeService(mocker.Mock())

    await service.get_all(collection, batch_size=50)  # act

    assert collection.batch_sizes == [50]
