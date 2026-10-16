import pytest

from mpt_extension_sdk.api.builders.deferred_handler import build_deferred_callback
from mpt_extension_sdk.api.responses import APIResponse
from mpt_extension_sdk.api.results import TaskResult


@pytest.fixture
def deferred_callback_factory(task_service):
    def factory(callback):
        return build_deferred_callback(
            callback=callback,
            handler_arguments={"agreement_id": "AGR-1"},
            task_service=task_service,
            task_id="TSK-1",
        )

    return factory


async def test_calls_handler_with_arguments(deferred_callback_factory, mocker):
    callback = mocker.AsyncMock(return_value=None)

    await deferred_callback_factory(callback)()  # act

    callback.assert_awaited_once_with(agreement_id="AGR-1")


async def test_stores_returned_task_result(deferred_callback_factory, mocker, task_service):
    callback = mocker.AsyncMock(
        return_value=TaskResult.reference("/public/v1/commerce/agreements/AGR-1")
    )

    await deferred_callback_factory(callback)()  # act

    task_service.set_result.assert_awaited_once_with(
        "TSK-1", "/public/v1/commerce/agreements/AGR-1"
    )


@pytest.mark.parametrize("outcome", [None, APIResponse.no_content()])
async def test_skips_result_for_other_outcomes(
    deferred_callback_factory, mocker, task_service, outcome
):
    callback = mocker.AsyncMock(return_value=outcome)

    await deferred_callback_factory(callback)()  # act

    task_service.set_result.assert_not_awaited()
