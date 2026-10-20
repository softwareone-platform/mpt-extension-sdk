from unittest.mock import call

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


@pytest.mark.parametrize(
    ("outcome", "expected_results"),
    [
        (
            TaskResult.reference("/public/v1/commerce/agreements/AGR-1"),
            [call("TSK-1", "/public/v1/commerce/agreements/AGR-1")],
        ),
        (None, []),
        (APIResponse.no_content(), []),
    ],
)
async def test_stores_only_task_result(mocker, task_service, outcome, expected_results):
    deferred_callback = build_deferred_callback(
        callback=mocker.AsyncMock(return_value=outcome),
        handler_arguments={},
        task_service=task_service,
        task_id="TSK-1",
    )

    await deferred_callback()  # act

    assert task_service.set_result.await_args_list == expected_results
