import pytest

from mpt_extension_sdk.api.auth import AuthContext
from mpt_extension_sdk.pipeline.builders import ContextResources
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.services.mpt_api_service.agreement import AgreementService
from mpt_extension_sdk.services.mpt_api_service.order import OrderService
from mpt_extension_sdk.settings.extension import BaseExtensionSettings


@pytest.fixture
def resources(mocker, runtime_settings):
    return ContextResources(
        auth=mocker.create_autospec(AuthContext, instance=True),
        ext_settings=mocker.create_autospec(BaseExtensionSettings, instance=True),
        mpt_api_service=mocker.AsyncMock(
            spec=MPTAPIService,
            agreements=mocker.AsyncMock(spec=AgreementService),
            orders=mocker.AsyncMock(spec=OrderService),
        ),
        runtime_settings=runtime_settings,
        vendor_mpt_api_service=mocker.AsyncMock(spec=MPTAPIService),
    )
