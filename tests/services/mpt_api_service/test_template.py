import pytest
from mpt_api_client.resources import AsyncCatalog, AsyncCommerce
from mpt_api_client.resources.catalog.products import AsyncProductsService
from mpt_api_client.resources.catalog.products_templates import AsyncTemplatesService
from mpt_api_client.resources.commerce.orders import AsyncOrdersService

from mpt_extension_sdk.models.template import Template
from mpt_extension_sdk.services.api_client_v2.mpt_api_client import AsyncMPTClient
from mpt_extension_sdk.services.mpt_api_service.template import TemplateService


@pytest.fixture
def template_service_factory(mocker):
    def factory():
        templates_query = mocker.Mock(spec=AsyncTemplatesService)
        templates_query.filter.return_value = templates_query
        templates_query.order_by.return_value = templates_query
        products_client = mocker.Mock(spec=AsyncProductsService)
        products_client.templates = mocker.Mock(return_value=templates_query)
        catalog_client = mocker.Mock(spec=AsyncCatalog)
        catalog_client.products = products_client
        client = mocker.Mock(spec=AsyncMPTClient)
        client.catalog = catalog_client
        return TemplateService(client), products_client.templates, templates_query

    return factory


async def test_get_template_returns_default_template(mocker, template_service_factory):
    service, templates_factory, templates_query = template_service_factory()
    templates_query.fetch_page = mocker.AsyncMock(return_value=[mocker.sentinel.api_template])
    from_payload = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.template.Template.from_payload",
        autospec=True,
        return_value="template-model",
    )

    result = await service.get_template("PROD-1", "Completed")

    assert result == "template-model"
    templates_factory.assert_called_once_with("PROD-1")
    templates_query.filter.assert_called_once_with(mocker.ANY)
    templates_query.order_by.assert_called_once_with("default")
    templates_query.fetch_page.assert_awaited_once_with(limit=1)
    from_payload.assert_called_once_with(mocker.sentinel.api_template)


async def test_get_template_returns_named_template(mocker, template_service_factory):
    api_template = mocker.Mock()
    service, _, templates_query = template_service_factory()
    templates_query.fetch_page = mocker.AsyncMock(return_value=[api_template])
    from_payload = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.template.Template.from_payload",
        autospec=True,
        return_value="named-template",
    )

    result = await service.get_template("PROD-1", "Completed", name="Welcome")

    assert result == "named-template"
    templates_query.filter.assert_called_once_with(mocker.ANY)
    templates_query.order_by.assert_called_once_with("default")
    templates_query.fetch_page.assert_awaited_once_with(limit=1)
    from_payload.assert_called_once_with(api_template)


async def test_get_template_returns_none_when_missing(mocker, template_service_factory):
    service, _, templates_query = template_service_factory()
    templates_query.fetch_page = mocker.AsyncMock(return_value=[])
    from_payload = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.template.Template.from_payload",
        autospec=True,
    )

    result = await service.get_template("PROD-1", "Completed")

    assert result is None
    from_payload.assert_not_called()


async def test_get_asset_template_by_name_returns_one(mocker, template_service_factory):
    api_template = mocker.Mock()
    service, _, templates_query = template_service_factory()
    templates_query.fetch_page = mocker.AsyncMock(return_value=[api_template])
    from_payload = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.template.Template.from_payload",
        autospec=True,
        return_value="asset-template",
    )

    result = await service.get_asset_template_by_name("PROD-1", "Asset Template")

    assert result == "asset-template"
    templates_query.filter.assert_called_once_with(mocker.ANY)
    templates_query.fetch_page.assert_awaited_once_with(limit=1)
    from_payload.assert_called_once_with(api_template)


async def test_get_asset_template_by_name_returns_none(mocker, template_service_factory):
    service, _, templates_query = template_service_factory()
    templates_query.fetch_page = mocker.AsyncMock(return_value=[])
    from_payload = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.template.Template.from_payload",
        autospec=True,
    )

    result = await service.get_asset_template_by_name("PROD-1", "Asset Template")

    assert result is None
    from_payload.assert_not_called()


async def test_get_order_querying_template_returns_one(mocker, template_service_factory):
    api_template = mocker.Mock()
    service, _, templates_query = template_service_factory()
    templates_query.fetch_page = mocker.AsyncMock(return_value=[api_template])
    from_payload = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.template.Template.from_payload",
        autospec=True,
        return_value="querying-template",
    )

    result = await service.get_order_querying_template("PROD-1")

    assert result == "querying-template"
    templates_query.filter.assert_called_once_with(mocker.ANY)
    templates_query.fetch_page.assert_awaited_once_with(limit=1)
    from_payload.assert_called_once_with(api_template)


async def test_get_order_querying_template_returns_none(mocker, template_service_factory):
    service, _, templates_query = template_service_factory()
    templates_query.fetch_page = mocker.AsyncMock(return_value=[])
    from_payload = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.template.Template.from_payload",
        autospec=True,
    )

    result = await service.get_order_querying_template("PROD-1")

    assert result is None
    from_payload.assert_not_called()


async def test_set_order_template_updates_order(mocker):
    order_template = mocker.Mock(spec=Template)
    order_template.to_dict.return_value = {"id": "TPL-1"}
    orders_client = mocker.AsyncMock(spec=AsyncOrdersService)
    orders_client.update = mocker.AsyncMock()
    commerce_client = mocker.AsyncMock(spec=AsyncCommerce)
    commerce_client.orders = orders_client
    client = mocker.Mock(spec=AsyncMPTClient)
    client.commerce = commerce_client
    service = TemplateService(client)

    await service.set_order_template("ORD-1", order_template)  # act

    order_template.to_dict.assert_called_once_with()
    orders_client.update.assert_awaited_once_with("ORD-1", {"template": {"id": "TPL-1"}})
