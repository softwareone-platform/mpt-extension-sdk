import pytest
from mpt_api_client.exceptions import MPTHttpError

from mpt_extension_sdk.errors.pipeline import CancelError, DeferError
from mpt_extension_sdk.runtime.task_transitions import SafeTaskTransitions


@pytest.fixture
def transitions(task_service, logger):
    return SafeTaskTransitions(task_service, logger)


async def test_complete_calls_service(transitions, task_service):
    await transitions.complete("TSK-1")  # act

    task_service.complete.assert_awaited_once_with("TSK-1")


async def test_fail_passes_reason(transitions, task_service):
    await transitions.fail("TSK-1", reason="boom")  # act

    task_service.fail.assert_awaited_once_with("TSK-1", reason="boom")


@pytest.mark.parametrize("status_code", [404, 409])
async def test_complete_ignores_finalized_rejection(transitions, task_service, status_code):
    task_service.complete.side_effect = MPTHttpError(status_code, "final", "")

    await transitions.complete("TSK-1")  # act

    task_service.complete.assert_awaited_once_with("TSK-1")


async def test_fail_ignores_finalized_rejection(transitions, task_service):
    task_service.fail.side_effect = MPTHttpError(409, "final", "")

    await transitions.fail("TSK-1")  # act

    task_service.fail.assert_awaited_once_with("TSK-1", reason=None)


async def test_reschedule_ignores_finalized_rejection(transitions, task_service):
    task_service.reschedule.side_effect = MPTHttpError(404, "final", "")

    await transitions.reschedule("TSK-1")  # act

    task_service.reschedule.assert_awaited_once_with("TSK-1")


async def test_complete_reraises_other_http_errors(transitions, task_service):
    task_service.complete.side_effect = MPTHttpError(500, "boom", "")

    with pytest.raises(MPTHttpError):
        await transitions.complete("TSK-1")


async def test_defer_error_reschedules(transitions, task_service):
    await transitions.transition_on_error("TSK-1", DeferError("later"))  # act

    task_service.reschedule.assert_awaited_once_with("TSK-1")


async def test_cancel_error_fails_with_reason(transitions, task_service):
    await transitions.transition_on_error("TSK-1", CancelError("cancelled"))  # act

    task_service.fail.assert_awaited_once_with("TSK-1", reason="cancelled")


async def test_unexpected_error_fails(transitions, task_service):
    await transitions.transition_on_error("TSK-1", RuntimeError("boom"))  # act

    task_service.fail.assert_awaited_once_with("TSK-1", reason="Unexpected error")
