import pytest

from mpt_extension_sdk.api.context import AuthenticatedRequestContext
from mpt_extension_sdk.pipeline.builders import WebhookContextBuilder
from mpt_extension_sdk.webhooks import WebhookContext


@pytest.fixture
def request_context(mocker):
    return mocker.create_autospec(AuthenticatedRequestContext, instance=True)


async def test_webhook_context_has_payload(logger, request_context, resources):
    builder = WebhookContextBuilder(
        handler_logger=logger, payload={"id": "ORD-1"}, request_context=request_context
    )

    result = await builder.build(resources)

    assert isinstance(result, WebhookContext)
    assert (result.logger, result.payload, result.request) == (
        logger,
        {"id": "ORD-1"},
        request_context,
    )
    assert (result.auth, result.vendor_mpt_api_service) == (
        resources.auth,
        resources.vendor_mpt_api_service,
    )
