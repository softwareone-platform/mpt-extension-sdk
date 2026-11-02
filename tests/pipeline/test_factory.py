import pytest

from mpt_extension_sdk.api.auth import AuthContext, AuthenticationError
from mpt_extension_sdk.pipeline.builders import ContextBuilder, ContextResources
from mpt_extension_sdk.pipeline.factory import RouteContextFactory
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.settings.extension import BaseExtensionSettings


@pytest.fixture
def auth(mocker):
    return mocker.Mock(spec=AuthContext, extension_id="EXT-1")


@pytest.fixture
def account_service(mocker):
    return mocker.AsyncMock(spec=MPTAPIService)


@pytest.fixture
def vendor_service(mocker):
    return mocker.AsyncMock(spec=MPTAPIService)


@pytest.fixture
def service_type(mocker, account_service, vendor_service):
    service_type = mocker.create_autospec(MPTAPIService)
    service_type.from_auth_context.return_value = account_service
    service_type.from_vendor_account.return_value = vendor_service
    return service_type


@pytest.fixture
def extension_settings(mocker):
    return mocker.create_autospec(BaseExtensionSettings, instance=True)


@pytest.fixture(autouse=True)
def process_settings(mocker, runtime_settings, extension_settings):
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_runtime_settings",
        autospec=True,
        return_value=runtime_settings,
    )
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_extension_settings",
        autospec=True,
        return_value=extension_settings,
    )


@pytest.fixture
def factory(service_type):
    return RouteContextFactory(service_type)


@pytest.fixture
def builder(mocker):
    builder = mocker.create_autospec(ContextBuilder, instance=True)
    builder.build.return_value = mocker.sentinel.context
    return builder


async def test_build_returns_builder_context(mocker, factory, builder, auth):
    result = await factory.build(builder, auth)

    assert result is mocker.sentinel.context


async def test_build_passes_shared_resources(
    factory, builder, auth, runtime_settings, extension_settings, account_service, vendor_service
):
    await factory.build(builder, auth)  # act

    builder.build.assert_awaited_once_with(
        ContextResources(
            auth=auth,
            ext_settings=extension_settings,
            mpt_api_service=account_service,
            runtime_settings=runtime_settings,
            vendor_mpt_api_service=vendor_service,
        )
    )


async def test_build_scopes_services(factory, builder, auth, runtime_settings, service_type):
    await factory.build(builder, auth)  # act

    service_type.from_auth_context.assert_awaited_once_with(
        base_url=runtime_settings.mpt_api_base_url, auth=auth
    )
    service_type.from_vendor_account.assert_awaited_once_with(
        base_url=runtime_settings.mpt_api_base_url
    )


async def test_build_rejects_mismatched_ext_id(factory, builder, auth, service_type):
    auth.extension_id = "EXT-2"

    with pytest.raises(AuthenticationError):
        await factory.build(builder, auth)

    service_type.from_auth_context.assert_not_awaited()
    builder.build.assert_not_awaited()
