import datetime as dt
from collections.abc import Callable

import pytest
from freezegun import freeze_time

from mpt_extension_sdk.api.builders.event_delivery import EventDeliveryHandler
from mpt_extension_sdk.api.builders.task_timing import EVENT_RETENTION_SECONDS
from mpt_extension_sdk.api.models.events import EventResponse
from mpt_extension_sdk.errors.runtime import ValidationError
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.pipeline import EventBaseContext
from mpt_extension_sdk.routing import EventDeliveryMode, EventRouteDefinition, RouteType
from mpt_extension_sdk.runtime.logging import event_id_ctx, order_id_ctx, task_id_ctx

# Shortly after the delivery time of the task_event fixture, so the event of every
# delivery under test was enqueued in the past, as the framework delivers it.
DELIVERED_AT = "2026-08-11T17:05:00Z"


@pytest.fixture
def event_callback(mocker):
    return mocker.AsyncMock(spec=Callable)


@pytest.fixture
def event_route(event_callback):
    return EventRouteDefinition(
        name="orders-purchase",
        path="/events/orders/purchase",
        route_type=RouteType.EVENT,
        callback=event_callback,
        event="platform.commerce.order.purchased",
        delivery_mode=EventDeliveryMode.TASK,
    )


@pytest.fixture
def event_context(mocker):
    return mocker.Mock(spec=EventBaseContext)


@pytest.fixture
def extension_app(mocker, event_context):
    app = mocker.create_autospec(ExtensionApp, instance=True)
    app.build_context.return_value = event_context
    return app


@pytest.fixture
def delivery_handler(
    event_route, extension_app, context_factory, task_service, async_task_runner, logger
):
    return EventDeliveryHandler(
        route=event_route,
        extension_app=extension_app,
        context_factory=context_factory,
        task_service=task_service,
        runner=async_task_runner,
        handler_logger=logger,
    )


@pytest.fixture
def base_context(mocker):
    return mocker.sentinel.base_context


@pytest.fixture
def build_event_context(authenticate, context_factory, base_context):
    context_factory.build.return_value = base_context
    return context_factory.build


@pytest.fixture
def event_span(mocker):
    return mocker.sentinel.span


@pytest.fixture
def start_event_span_mock(mocker, event_span):
    start_event_span = mocker.patch(
        "mpt_extension_sdk.api.builders.event_delivery.start_event_span", autospec=True
    )
    start_event_span.return_value.__enter__.return_value = event_span
    return start_event_span


@pytest.fixture
def get_business_attributes_mock(mocker):
    return mocker.patch(
        "mpt_extension_sdk.api.builders.event_delivery.get_business_attributes",
        autospec=True,
        return_value={"order.id": "ORD-001", "agreement.id": "AGR-001"},
    )


@pytest.fixture
def set_attributes_mock(mocker):
    return mocker.patch(
        "mpt_extension_sdk.api.builders.event_delivery.set_attributes", autospec=True
    )


@pytest.fixture
def record_exception_mock(mocker):
    return mocker.patch(
        "mpt_extension_sdk.api.builders.event_delivery.record_exception", autospec=True
    )


@pytest.fixture
def submitted_callback(
    build_event_context,
    run,
    async_task_runner,
    start_event_span_mock,
    get_business_attributes_mock,
    set_attributes_mock,
    record_exception_mock,
):
    async def factory():
        await run()
        execution = async_task_runner.submit.call_args.kwargs["execution"]
        return execution.task_callback

    return factory


@freeze_time(DELIVERED_AT)
async def test_queued_defers_watchdog(build_event_context, run):
    result = await run()

    assert result == EventResponse.reschedule(300)


async def test_queued_starts_and_submits(build_event_context, run, task_service, async_task_runner):
    await run()  # act

    task_service.start.assert_awaited_once_with("TSK-001")
    async_task_runner.submit.assert_called_once()


async def test_final_task_acknowledged(build_event_context, run, task_service, task_factory):
    task_service.get.return_value = task_factory("Completed")

    result = await run()

    assert result == EventResponse.ok()


async def test_context_built_from_event(build_event_context, run, task_event):
    await run()  # act

    assert build_event_context.call_args.args[0].event is task_event


async def test_context_adapted_for_route(
    build_event_context, run, extension_app, event_route, base_context
):
    await run()  # act

    extension_app.build_context.assert_called_once_with(event_route, base_context)


async def test_cancels_when_adapter_rejects_context(build_event_context, run, extension_app):
    extension_app.build_context.side_effect = TypeError("adapter returned the wrong type")

    result = await run()

    assert result == EventResponse.cancel(reason="Non-recoverable context error")


async def test_cancels_unsupported_object_type(build_event_context, run):
    build_event_context.side_effect = ValidationError("Unsupported context type: Subscription")

    result = await run()

    assert result == EventResponse.cancel(reason="Non-recoverable context error")


async def test_submitted_execution_runs_handler(
    submitted_callback, event_callback, task_event, event_context
):
    task_callback = await submitted_callback()

    await task_callback()  # act

    event_callback.assert_awaited_once_with(task_event, event_context)


async def test_submitted_execution_opens_event_span(
    submitted_callback, start_event_span_mock, set_attributes_mock, event_span, task_event
):
    task_callback = await submitted_callback()

    await task_callback()  # act

    start_event_span_mock.assert_called_once_with(
        "/events/orders/purchase", task_based=True, event=task_event
    )
    set_attributes_mock.assert_called_once_with(
        event_span, {"order.id": "ORD-001", "agreement.id": "AGR-001"}
    )


async def test_submitted_execution_sets_log_context(submitted_callback, task_event):
    task_callback = await submitted_callback()

    await task_callback()  # act

    assert (event_id_ctx.get(), task_id_ctx.get(), order_id_ctx.get()) == (
        task_event.id,
        "TSK-001",
        "ORD-001",
    )


async def test_submitted_execution_records_error(
    submitted_callback, event_callback, record_exception_mock, event_span
):
    error = RuntimeError("boom")
    event_callback.side_effect = error
    task_callback = await submitted_callback()

    with pytest.raises(RuntimeError):
        await task_callback()

    record_exception_mock.assert_called_once_with(event_span, error)


async def test_watchdog_capped_by_event_retention(build_event_context, run, task_event):
    hundred_seconds_left = task_event.details.enqueue_time + dt.timedelta(
        seconds=EVENT_RETENTION_SECONDS - 100
    )

    with freeze_time(hundred_seconds_left):
        result = await run()

    assert result == EventResponse.reschedule(40)


async def test_event_id_in_log_context(build_event_context, run, task_event):
    await run()  # act

    assert event_id_ctx.get() == task_event.id
