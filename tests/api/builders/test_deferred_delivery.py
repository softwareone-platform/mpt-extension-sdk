import pytest
from fastapi import Request
from mpt_api_client.exceptions import MPTAPIError, MPTError
from starlette.datastructures import Headers, QueryParams

from mpt_extension_sdk.api.auth import AuthenticationError
from mpt_extension_sdk.api.builders.deferred_delivery import DeferredCallHandler
from mpt_extension_sdk.api.context import APIContext
from mpt_extension_sdk.api.errors import ValidationError
from mpt_extension_sdk.api.models.errors import ErrorDetail
from mpt_extension_sdk.api.models.events import EventResponse
from mpt_extension_sdk.errors.runtime import AsyncTasksRunnerError, ConfigError
from mpt_extension_sdk.models.task import Task, TaskStatus
from mpt_extension_sdk.pipeline import RouteContextFactory
from mpt_extension_sdk.routing import RouteType
from mpt_extension_sdk.routing.enums import HTTPMethod
from mpt_extension_sdk.routing.models import APIRouteDefinition
from mpt_extension_sdk.tasks import TaskHandle


@pytest.fixture(autouse=True)
def arguments_builder(mocker):
    builder_type = mocker.patch(
        "mpt_extension_sdk.api.builders.deferred_delivery.APIHandlerArgumentsBuilder",
        autospec=True,
    )
    builder = builder_type.return_value
    builder.parse_request_body.return_value = {"agreementId": "AGR-1"}
    builder.build.return_value = {"agreement_id": "AGR-1"}
    return builder


@pytest.fixture(autouse=True)
def authenticate(mocker):
    return mocker.patch(
        "mpt_extension_sdk.api.builders.task_delivery.RequestAuthenticationService.authenticate",
        autospec=True,
    )


@pytest.fixture
def context_factory(mocker):
    factory = mocker.create_autospec(RouteContextFactory, instance=True)
    factory.build.return_value = mocker.Mock(spec=APIContext)
    return factory


@pytest.fixture
def delivery_handler(mocker, context_factory, task_service, async_task_runner, logger):
    return DeferredCallHandler(
        route=APIRouteDefinition(
            callback=mocker.AsyncMock(),
            method=HTTPMethod.POST,
            name="agreement-sync",
            path="/agreements/sync",
            route_type=RouteType.API,
        ),
        context_factory=context_factory,
        task_service=task_service,
        runner=async_task_runner,
        handler_logger=logger,
    )


@pytest.fixture
def http_request(mocker):
    http_request = mocker.Mock(spec=Request)
    http_request.query_params = QueryParams("")
    http_request.headers = Headers({})
    http_request.method = "POST"
    http_request.url = "https://extension.test/agreements/sync"
    return http_request


@pytest.mark.parametrize(
    ("task_lookup", "expected"),
    [
        ({"side_effect": MPTError("tasks API unavailable")}, EventResponse.reschedule()),
        ({"return_value": Task(id="TSK-001", status=TaskStatus.COMPLETED)}, EventResponse.ok()),
        ({"return_value": Task(id="TSK-001", status=TaskStatus.FAILED)}, EventResponse.ok()),
        (
            {"return_value": Task(id="TSK-001", status=TaskStatus.PROCESSING)},
            EventResponse.reschedule(300),
        ),
    ],
)
async def test_answers_task_state(
    delivery_handler, http_request, task_service, task_lookup, expected
):
    task_service.get.configure_mock(**task_lookup)

    result = await delivery_handler.execute(  # noqa: WPS204
        request=http_request, task_id="TSK-001", delivery=None
    )

    assert result == expected
    task_service.start.assert_not_awaited()


async def test_cancels_on_authentication_failure(delivery_handler, http_request, authenticate):
    authenticate.side_effect = AuthenticationError

    result = await delivery_handler.execute(request=http_request, task_id="TSK-001", delivery=None)

    assert result == EventResponse.cancel(reason="Authentication failed")


@pytest.mark.parametrize(
    "runner_state",
    [{"has_capacity.return_value": False}, {"reserve.return_value.__enter__.return_value": False}],
)
async def test_defers_without_claiming(
    delivery_handler, http_request, task_service, async_task_runner, runner_state
):
    async_task_runner.configure_mock(**runner_state)

    result = await delivery_handler.execute(request=http_request, task_id="TSK-001", delivery=None)

    assert result == EventResponse.reschedule(300)
    task_service.start.assert_not_awaited()


async def test_running_elsewhere_skips_context(
    delivery_handler, http_request, context_factory, task_service, task_factory
):
    task_service.get.return_value = task_factory(TaskStatus.PROCESSING, started_seconds_ago=600)

    await delivery_handler.execute(request=http_request, task_id="TSK-001", delivery=None)  # act

    context_factory.build.assert_not_awaited()


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            ValidationError(errors=[ErrorDetail(pointer="#/agreementId", detail="Field required")]),
            EventResponse.cancel(reason="Invalid request payload"),
        ),
        (ConfigError("bad"), EventResponse.cancel(reason="Non-recoverable context error")),
        (AuthenticationError("bad"), EventResponse.cancel(reason="Authentication failed")),
        (MPTError("accounts API unavailable"), EventResponse.reschedule()),
    ],
)
async def test_answers_failed_context_build(
    delivery_handler, http_request, context_factory, task_service, error, expected
):
    context_factory.build.side_effect = error

    result = await delivery_handler.execute(request=http_request, task_id="TSK-001", delivery=None)

    assert result == expected
    task_service.start.assert_not_awaited()


async def test_cancels_invalid_request_body(
    delivery_handler, http_request, arguments_builder, task_service
):
    arguments_builder.parse_request_body.side_effect = ValidationError(
        errors=[ErrorDetail(pointer="#", detail="Invalid JSON payload")]
    )

    result = await delivery_handler.execute(request=http_request, task_id="TSK-001", delivery=None)

    assert result == EventResponse.cancel(reason="Invalid request payload")
    task_service.start.assert_not_awaited()


@pytest.mark.parametrize(
    ("claim", "submit", "expected", "reschedules"),
    [
        ({}, {}, EventResponse.reschedule(300), 0),
        (
            {"side_effect": MPTAPIError(status_code=409, message="conflict", payload={})},
            {},
            EventResponse.reschedule(300),
            0,
        ),
        (
            {},
            {"side_effect": AsyncTasksRunnerError("boom", task_id="TSK-001")},
            EventResponse.reschedule(),
            1,
        ),
        ({}, {"return_value": False}, EventResponse.reschedule(), 1),
    ],
)
async def test_answers_claim_and_submit(
    delivery_handler,
    http_request,
    task_service,
    async_task_runner,
    claim,
    submit,
    expected,
    reschedules,
):
    task_service.start.configure_mock(**claim)
    async_task_runner.submit.configure_mock(**submit)

    result = await delivery_handler.execute(request=http_request, task_id="TSK-001", delivery=None)

    assert result == expected
    assert task_service.reschedule.await_count == reschedules


async def test_context_carries_delivered_task(
    delivery_handler, http_request, context_factory, task_service
):
    await delivery_handler.execute(request=http_request, task_id="TSK-001", delivery=None)  # act

    builder = context_factory.build.call_args.args[0]
    assert builder.task == TaskHandle(id="TSK-001", task_service=task_service)


async def test_submitted_execution_runs_handler(
    delivery_handler, http_request, async_task_runner, arguments_builder
):
    await delivery_handler.execute(request=http_request, task_id="TSK-001", delivery=None)
    execution = async_task_runner.submit.call_args.kwargs["execution"]

    await execution.task_callback()  # act

    delivery_handler.route.callback.assert_awaited_once_with(**arguments_builder.build.return_value)


@pytest.mark.parametrize(
    ("started_seconds_ago", "expected_delay"),
    [(None, 300), (900, 900), (7200, 1800)],
)
def test_watchdog_follows_elapsed_processing(
    delivery_handler, task_factory, started_seconds_ago, expected_delay
):
    task = task_factory(
        TaskStatus.PROCESSING, created_seconds_ago=604770, started_seconds_ago=started_seconds_ago
    )

    result = delivery_handler.watchdog_delay(task, None)

    assert result == expected_delay
