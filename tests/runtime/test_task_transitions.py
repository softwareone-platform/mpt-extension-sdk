import logging

import pytest
from mpt_api_client.exceptions import MPTError, MPTHttpError

from mpt_extension_sdk.errors.pipeline import CancelError, DeferError
from mpt_extension_sdk.models.task import Task
from mpt_extension_sdk.runtime.task_transitions import SafeTaskTransitions


@pytest.fixture
def handler_logger(mocker):
    return mocker.Mock(spec=logging.Logger)


@pytest.fixture
def transitions(task_service, handler_logger):
    return SafeTaskTransitions(task_service, handler_logger)


@pytest.fixture
def task_in(task_service):
    def factory(status):
        task_service.get.return_value = Task(id="TSK-1", status=status)

    return factory


async def test_complete_calls_service(transitions, task_service):
    await transitions.complete("TSK-1")  # act

    task_service.complete.assert_awaited_once_with("TSK-1")


async def test_fail_passes_reason(transitions, task_service):
    await transitions.fail("TSK-1", reason="boom")  # act

    task_service.fail.assert_awaited_once_with("TSK-1", reason="boom")


@pytest.mark.parametrize("status_code", [404, 409])
async def test_complete_ignores_finalized_rejection(
    transitions, task_service, task_in, status_code
):
    task_in("Failed")
    task_service.complete.side_effect = MPTHttpError(status_code, "final", "")

    await transitions.complete("TSK-1")  # act

    task_service.complete.assert_awaited_once_with("TSK-1")


async def test_fail_ignores_finalized_rejection(transitions, task_service, task_in):
    task_in("Failed")
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


async def test_final_task_conflict_warns(transitions, task_service, task_in, handler_logger):
    task_in("Completed")
    task_service.complete.side_effect = MPTHttpError(409, "conflict", "")

    await transitions.complete("TSK-1")  # act

    assert handler_logger.warning.call_args.args[1:] == ("TSK-1", "completed")


async def test_final_task_conflict_is_not_an_error(
    transitions, task_service, task_in, handler_logger
):
    task_in("Completed")
    task_service.complete.side_effect = MPTHttpError(409, "conflict", "")

    await transitions.complete("TSK-1")  # act

    handler_logger.error.assert_not_called()


async def test_illegal_transition_names_the_status(
    transitions, task_service, task_in, handler_logger
):
    task_in("Queued")
    task_service.reschedule.side_effect = MPTHttpError(409, "conflict", "")

    await transitions.reschedule("TSK-1")  # act

    assert handler_logger.error.call_args.args[1:3] == ("TSK-1", "queued")


async def test_illegal_transition_is_not_a_warning(
    transitions, task_service, task_in, handler_logger
):
    task_in("Queued")
    task_service.reschedule.side_effect = MPTHttpError(409, "conflict", "")

    await transitions.reschedule("TSK-1")  # act

    handler_logger.warning.assert_not_called()


async def test_conflict_reads_the_current_task(transitions, task_service, task_in):
    task_in("Queued")
    task_service.reschedule.side_effect = MPTHttpError(409, "conflict", "")

    await transitions.reschedule("TSK-1")  # act

    task_service.get.assert_awaited_once_with("TSK-1")


async def test_missing_task_skips_the_read(transitions, task_service):
    task_service.complete.side_effect = MPTHttpError(404, "gone", "")

    await transitions.complete("TSK-1")  # act

    task_service.get.assert_not_awaited()


async def test_unreadable_status_after_conflict(transitions, task_service, handler_logger):
    task_service.complete.side_effect = MPTHttpError(409, "conflict", "")
    task_service.get.side_effect = MPTError("tasks API unavailable")

    await transitions.complete("TSK-1")  # act

    handler_logger.exception.assert_called_once()


async def test_defer_error_reschedules(transitions, task_service):
    await transitions.transition_on_error("TSK-1", DeferError("later"))  # act

    task_service.reschedule.assert_awaited_once_with("TSK-1")


async def test_cancel_error_fails_with_reason(transitions, task_service):
    await transitions.transition_on_error("TSK-1", CancelError("cancelled"))  # act

    task_service.fail.assert_awaited_once_with("TSK-1", reason="cancelled")


async def test_unexpected_error_fails(transitions, task_service):
    await transitions.transition_on_error("TSK-1", RuntimeError("boom"))  # act

    task_service.fail.assert_awaited_once_with("TSK-1", reason="Unexpected error")
