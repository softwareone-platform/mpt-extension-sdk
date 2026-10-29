import pytest

from mpt_extension_sdk.api.context import AuthenticatedRequestContext
from mpt_extension_sdk.pipeline.builders import APIContextBuilder
from mpt_extension_sdk.tasks import TaskHandle


@pytest.fixture
def request_context(mocker):
    return mocker.create_autospec(AuthenticatedRequestContext, instance=True)


async def test_api_context_has_request_and_resources(logger, request_context, resources):
    builder = APIContextBuilder(handler_logger=logger, request_context=request_context)

    result = await builder.build(resources)

    assert (result.logger, result.request, result.task) == (logger, request_context, None)
    assert (result.auth, result.vendor_mpt_api_service) == (
        resources.auth,
        resources.vendor_mpt_api_service,
    )


async def test_api_context_carries_task(logger, request_context, resources, task_service):
    task = TaskHandle(id="TSK-1", task_service=task_service)
    builder = APIContextBuilder(handler_logger=logger, request_context=request_context, task=task)

    result = await builder.build(resources)

    assert result.task is task
