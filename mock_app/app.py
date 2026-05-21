from mock_app.api.routes.api import api_router
from mock_app.api.routes.event import orders_router
from mock_app.mocks.api_service import ExtMPTAPIService
from mpt_extension_sdk import ExtensionApp

ext_app = ExtensionApp(prefix="/api/v2", mpt_api_service_type=ExtMPTAPIService, version="6.0.0")
ext_app.include_router(api_router)
ext_app.include_router(orders_router)
