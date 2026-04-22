from mock_app.api.routes import orders_router
from mock_app.mocks.api_service import ExtMPTAPIService
from mpt_extension_sdk import ExtensionApp

ext_app = ExtensionApp(prefix="/api/v2", mpt_api_service_type=ExtMPTAPIService)
ext_app.include_router(orders_router)
