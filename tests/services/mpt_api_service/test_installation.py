from collections.abc import Callable

import pytest
from mpt_api_client import RQLQuery
from mpt_api_client.http.types import Response
from mpt_api_client.models.meta import Meta, Pagination
from mpt_api_client.models.model_collection import ModelCollection
from mpt_api_client.resources.integration.installations import (
    AsyncInstallationsService,
)
from mpt_api_client.resources.integration.installations import (
    Installation as ClientInstallation,
)

from mpt_extension_sdk.services.mpt_api_service.installation import InstallationService


@pytest.fixture
def installation_service_factory(mocker, async_mpt_client):
    def factory():
        installations_service = mocker.Mock(spec=AsyncInstallationsService)
        async_mpt_client.integration.installations = installations_service
        return InstallationService(async_mpt_client), installations_service

    return factory


@pytest.fixture
def installation_collection_factory(mocker):
    def factory(total: int):
        return ModelCollection[ClientInstallation](
            resources=[],
            meta=Meta(
                response=mocker.Mock(spec=Response),
                pagination=Pagination(limit=0, offset=0, total=total),
            ),
        )

    return factory


async def test_exists_for_account_found(
    mocker, installation_service_factory, installation_collection_factory
):
    service, installations_client = installation_service_factory()
    page = installation_collection_factory(total=1)
    filtered_collection = mocker.Mock(spec=["fetch_page"])
    filtered_collection.fetch_page = mocker.AsyncMock(spec=Callable, return_value=page)
    installations_client.filter = mocker.Mock(return_value=filtered_collection)

    result = await service.exists_for_account(extension_id="EXT-1", account_id="ACC-1")

    assert result is True
    installations_client.filter.assert_called_once_with(
        RQLQuery(extension__id="EXT-1") & RQLQuery(account__id="ACC-1")
    )
    filtered_collection.fetch_page.assert_awaited_once_with(limit=0)


async def test_exists_for_account_not_found(
    installation_service_factory, installation_collection_factory, mocker
):
    service, installations_client = installation_service_factory()
    page = installation_collection_factory(total=0)
    filtered_collection = mocker.Mock(spec=["fetch_page"])
    filtered_collection.fetch_page = mocker.AsyncMock(spec=Callable, return_value=page)
    installations_client.filter = mocker.Mock(return_value=filtered_collection)

    result = await service.exists_for_account(extension_id="EXT-1", account_id="ACC-1")

    assert result is False


async def test_exists_for_account_propagates_api_error(mocker, installation_service_factory):
    service, installations_client = installation_service_factory()
    filtered_collection = mocker.Mock(spec=["fetch_page"])
    filtered_collection.fetch_page = mocker.AsyncMock(
        spec=Callable, side_effect=RuntimeError("boom")
    )
    installations_client.filter = mocker.Mock(return_value=filtered_collection)

    with pytest.raises(RuntimeError, match="boom"):
        await service.exists_for_account(extension_id="EXT-1", account_id="ACC-1")
