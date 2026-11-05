import pytest

from mpt_extension_sdk.api.builders.deferred_handler import build_deferred_callback
from mpt_extension_sdk.api.responses import APIResponse
from mpt_extension_sdk.api.results import TaskResult


async def test_calls_handler_with_arguments(mocker, task_service):
    callback = mocker.AsyncMock(return_value=None)
    deferred_callback = build_deferred_callback(
        callback=callback,
        handler_arguments={"agreement_id": "AGR-1"},
        task_service=task_service,
        task_id="TSK-1",
    )

    await deferred_callback()  # act

    callback.assert_awaited_once_with(agreement_id="AGR-1")


async def test_stores_task_result(mocker, task_service):
    deferred_callback = build_deferred_callback(
        callback=mocker.AsyncMock(
            return_value=TaskResult.reference("/public/v1/commerce/agreements/AGR-1")
        ),
        handler_arguments={},
        task_service=task_service,
        task_id="TSK-1",
    )

    await deferred_callback()  # act

    task_service.set_result.assert_awaited_once_with(
        "TSK-1", "/public/v1/commerce/agreements/AGR-1"
    )


@pytest.mark.parametrize("outcome", [None, APIResponse.no_content()])
async def test_skips_result_without_task_result(mocker, task_service, outcome):
    deferred_callback = build_deferred_callback(
        callback=mocker.AsyncMock(return_value=outcome),
        handler_arguments={},
        task_service=task_service,
        task_id="TSK-1",
    )

    await deferred_callback()  # act

    task_service.set_result.assert_not_awaited()
