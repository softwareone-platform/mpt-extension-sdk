import datetime as dt

import pytest
from fastapi import Request
from freezegun import freeze_time
from mpt_api_client.exceptions import MPTError

from mpt_extension_sdk.api.auth import AuthenticationError
from mpt_extension_sdk.api.builders.schedule_delivery import ScheduleDeliveryHandler
from mpt_extension_sdk.api.builders.task_timing import EVENT_RETENTION_SECONDS
from mpt_extension_sdk.api.models.events import EventResponse, ResponseEnum
from mpt_extension_sdk.errors.runtime import AsyncTasksRunnerError, ConfigError
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.runtime.logging import event_id_ctx

# Shortly after the delivery time of the task_event fixture, so the event of every
# delivery under test was enqueued in the past, as the framework delivers it.
DELIVERED_AT = "2026-08-11T17:05:00Z"


@pytest.fixture
def delivery_handler(schedule_route, task_service, async_task_runner, logger):
    return ScheduleDeliveryHandler(
        route=schedule_route,
        extension_app=ExtensionApp(),
        task_service=task_service,
        runner=async_task_runner,
        handler_logger=logger,
    )


@pytest.fixture
def run(mocker, delivery_handler, task_event):
    http_request = mocker.Mock(spec=Request)

    async def factory(event=task_event):
        return await delivery_handler.execute(request=http_request, task_id="TSK-001", event=event)

    return factory


@pytest.fixture
def build_schedule_context(mocker, schedule_context):
    mocker.patch(
        "mpt_extension_sdk.api.builders.task_delivery.RequestAuthenticationService.authenticate",
        autospec=True,
    )
    factory = mocker.patch(
        "mpt_extension_sdk.api.builders.schedule_delivery.RouteContextFactory.from_service_type",
        autospec=True,
    )
    factory.return_value.build_schedule_context = mocker.AsyncMock(return_value=schedule_context)
    return factory.return_value.build_schedule_context


@freeze_time(DELIVERED_AT)
async def test_queued_defers_watchdog(build_schedule_context, run):
    result = await run()

    assert result == EventResponse.reschedule(300)


async def test_queued_starts_and_submits(
    build_schedule_context, run, task_service, async_task_runner
):
    await run()  # act

    task_service.start.assert_awaited_once_with("TSK-001")
    async_task_runner.submit.assert_called_once()


async def test_submitted_execution_runs_handler(
    build_schedule_context, run, async_task_runner, schedule_callback, schedule_context
):
    await run()
    execution = async_task_runner.submit.call_args.kwargs["execution"]

    await execution.task_callback()

    schedule_callback.assert_awaited_once_with(schedule_context)


@freeze_time(DELIVERED_AT)
async def test_submitted_execution_deadline(build_schedule_context, run, async_task_runner):
    await run()

    execution = async_task_runner.submit.call_args.kwargs["execution"]

    assert execution.deadline_seconds == 7140


async def test_final_task_acknowledged(build_schedule_context, run, task_service, task_factory):
    task_service.get.return_value = task_factory("Completed")

    result = await run()

    assert result == EventResponse.ok()


async def test_final_task_skips_runner(
    build_schedule_context, run, task_service, task_factory, async_task_runner
):
    task_service.get.return_value = task_factory("Completed")

    await run()  # act

    async_task_runner.reserve.assert_not_called()


@freeze_time(DELIVERED_AT)
async def test_watchdog_defers_while_running(
    build_schedule_context, run, task_service, task_factory, async_task_runner
):
    task_service.get.return_value = task_factory("Processing", started_seconds_ago=600)
    async_task_runner.reserve.return_value.__enter__.return_value = False

    result = await run()

    assert result == EventResponse.reschedule(600)


async def test_watchdog_skips_acceptance(
    build_schedule_context, run, task_service, task_factory, async_task_runner
):
    task_service.get.return_value = task_factory("Processing", started_seconds_ago=600)
    async_task_runner.reserve.return_value.__enter__.return_value = False

    await run()  # act

    build_schedule_context.assert_not_awaited()


async def test_task_claimed_elsewhere_not_restarted(
    build_schedule_context, run, task_service, task_factory, task_conflict
):
    task_service.get.return_value = task_factory("Processing", started_seconds_ago=600)
    task_service.start.side_effect = task_conflict

    await run()  # act

    task_service.reschedule.assert_not_awaited()


async def test_task_claimed_elsewhere_skips_handler(
    build_schedule_context, run, task_service, task_factory, task_conflict, async_task_runner
):
    task_service.get.return_value = task_factory("Processing", started_seconds_ago=600)
    task_service.start.side_effect = task_conflict

    await run()  # act

    async_task_runner.submit.assert_not_called()


@freeze_time(DELIVERED_AT)
async def test_task_claimed_elsewhere_keeps_cadence(
    build_schedule_context, run, task_service, task_factory, task_conflict
):
    task_service.get.return_value = task_factory("Processing", started_seconds_ago=600)
    task_service.start.side_effect = task_conflict

    result = await run()

    assert result == EventResponse.reschedule(600)


async def test_rescheduled_starts_and_submits(
    build_schedule_context, run, task_service, task_factory, async_task_runner
):
    task_service.get.return_value = task_factory("Rescheduled")

    await run()  # act

    task_service.start.assert_awaited_once_with("TSK-001")
    async_task_runner.submit.assert_called_once()


async def test_defers_when_submit_fails(
    build_schedule_context, run, task_service, async_task_runner
):
    async_task_runner.submit.side_effect = AsyncTasksRunnerError("submit failed", "TSK-001")

    await run()  # act

    task_service.reschedule.assert_awaited_once_with("TSK-001")


async def test_defers_when_reschedule_fails(
    build_schedule_context, run, task_service, async_task_runner
):
    async_task_runner.submit.return_value = False
    task_service.reschedule.side_effect = MPTError("tasks API unavailable")

    result = await run()

    assert result == EventResponse.reschedule()


async def test_defers_when_submit_rejected(
    build_schedule_context, run, task_service, async_task_runner
):
    async_task_runner.submit.return_value = False

    await run()  # act

    task_service.reschedule.assert_awaited_once_with("TSK-001")


async def test_defers_when_fetch_fails(build_schedule_context, run, task_service):
    task_service.get.side_effect = MPTError("tasks API unavailable")

    result = await run()

    assert result == EventResponse.reschedule()


async def test_fetch_failure_log_names_handler(build_schedule_context, run, task_service, caplog):
    task_service.get.side_effect = MPTError("tasks API unavailable")

    await run()  # act

    assert "Schedule task could not be fetched" in caplog.messages


async def test_fetch_failure_skips_runner(
    build_schedule_context, run, task_service, async_task_runner
):
    task_service.get.side_effect = MPTError("tasks API unavailable")

    await run()  # act

    async_task_runner.reserve.assert_not_called()


async def test_defers_on_context_error(build_schedule_context, run):
    build_schedule_context.side_effect = MPTError("context failed")

    result = await run()

    assert result.response == ResponseEnum.DEFER


async def test_defers_on_start_error(build_schedule_context, run, task_service):
    task_service.start.side_effect = MPTError("start failed")

    result = await run()

    assert result.response == ResponseEnum.DEFER


async def test_cancels_on_auth_failure(mocker, run):
    mocker.patch(
        "mpt_extension_sdk.api.builders.task_delivery.RequestAuthenticationService.authenticate",
        side_effect=AuthenticationError,
    )

    result = await run()

    assert result == EventResponse.cancel(reason="Authentication failed")


async def test_final_task_ok_without_auth(mocker, run, task_service, task_factory):
    task_service.get.return_value = task_factory("Completed")
    mocker.patch(
        "mpt_extension_sdk.api.builders.task_delivery.RequestAuthenticationService.authenticate",
        side_effect=AuthenticationError,
    )

    result = await run()

    assert result == EventResponse.ok()


@pytest.mark.parametrize(
    ("error", "expected_reason"),
    [
        (ConfigError("invalid extension configuration"), "Non-recoverable context error"),
        (AuthenticationError("token rejected"), "Authentication failed"),
    ],
)
async def test_cancels_unrecoverable_context(build_schedule_context, run, error, expected_reason):
    build_schedule_context.side_effect = error

    result = await run()

    assert result == EventResponse.cancel(reason=expected_reason)


@pytest.mark.parametrize(
    ("started_seconds_ago", "expected_delay"),
    [(None, 300), (600, 600), (7200, 1800)],
)
@freeze_time(DELIVERED_AT)
def test_watchdog_delay_backoff(
    delivery_handler, task_factory, task_event, started_seconds_ago, expected_delay
):
    task = task_factory("Processing", started_seconds_ago=started_seconds_ago)

    result = delivery_handler.watchdog_delay(task, task_event)

    assert result == expected_delay


def test_watchdog_delay_floors_near_expiry(delivery_handler, task_factory, task_event):
    thirty_seconds_left = task_event.details.enqueue_time + dt.timedelta(
        seconds=EVENT_RETENTION_SECONDS - 30
    )

    with freeze_time(thirty_seconds_left):
        result = delivery_handler.watchdog_delay(
            task_factory("Processing", started_seconds_ago=3600), task_event
        )

    assert result == 1


async def test_watchdog_capped_by_event_retention(build_schedule_context, run, task_event):
    hundred_seconds_left = task_event.details.enqueue_time + dt.timedelta(
        seconds=EVENT_RETENTION_SECONDS - 100
    )

    with freeze_time(hundred_seconds_left):
        result = await run()

    assert result == EventResponse.reschedule(40)


async def test_event_reaches_the_context(build_schedule_context, run, task_event):
    await run()  # act

    assert build_schedule_context.call_args.kwargs["event"] is task_event


async def test_event_id_in_log_context(build_schedule_context, run, task_event):
    await run()  # act

    assert event_id_ctx.get() == task_event.id
