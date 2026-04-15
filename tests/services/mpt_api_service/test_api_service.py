from mpt_extension_sdk.services.mpt_api_service.api_service import MPTAPIService


def test_api_service_composes_expected_services(mocker):  # noqa: WPS218
    client = mocker.Mock()

    result = MPTAPIService(client)

    assert result.client is client
    assert hasattr(result, "agreements")
    assert hasattr(result, "assets")
    assert hasattr(result, "products")
    assert hasattr(result, "product_items")
    assert hasattr(result, "orders")
    assert hasattr(result, "subscriptions")
    assert hasattr(result, "tasks")
    assert hasattr(result, "templates")
    assert not hasattr(result, "notifications")


def test_api_service_from_config(mocker):
    client = mocker.Mock()
    mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.api_service.build_mpt_client",
        autospec=True,
        return_value=client,
    )

    result = MPTAPIService.from_config("https://api.example.com", "token-1")

    assert isinstance(result, MPTAPIService)
    assert result.client is client
