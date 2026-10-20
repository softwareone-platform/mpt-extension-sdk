import datetime as dt
from collections.abc import Callable

import pytest
from mpt_api_client.exceptions import MPTAPIError

from mpt_extension_sdk.models.task import Task
from mpt_extension_sdk.pipeline import ScheduleContext
from mpt_extension_sdk.routing import RouteType, ScheduleRouteDefinition
from mpt_extension_sdk.runtime.async_tasks import AsyncTaskRunner
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.services.mpt_api_service.task import TaskService


@pytest.fixture
def task_factory():
    def factory(status, *, created_seconds_ago=0, started_seconds_ago=None, task_parameters=None):
        now = dt.datetime.now(dt.UTC)
        created_at = now - dt.timedelta(seconds=created_seconds_ago)
        audit = {"created": {"at": created_at.isoformat()}}
        if started_seconds_ago is not None:
            started_at = now - dt.timedelta(seconds=started_seconds_ago)
            audit["started"] = {"at": started_at.isoformat()}
        return Task.from_payload({
            "id": "TSK-001",
            "status": status,
            "audit": audit,
            "parameters": task_parameters,
        })

    return factory


@pytest.fixture
def task_conflict():
    """The platform rejection of a claim another execution already holds."""
    return MPTAPIError(status_code=409, message="conflict", payload={})


@pytest.fixture
def task_service(mocker, task_factory):
    service = mocker.AsyncMock(spec=TaskService)
    service.get.return_value = task_factory("Queued")
    return service


@pytest.fixture
def async_task_runner(mocker):
    runner = mocker.MagicMock(spec=AsyncTaskRunner)
    runner.has_capacity.return_value = True
    runner.is_running.return_value = False
    runner.reserve.return_value.__enter__.return_value = True
    runner.submit.return_value = True
    return runner


@pytest.fixture
def schedule_callback(mocker):
    return mocker.AsyncMock(spec=Callable)


@pytest.fixture
def schedule_route(schedule_callback):
    return ScheduleRouteDefinition(
        name="agreements-sync",
        path="/schedules/agreements",
        route_type=RouteType.SCHEDULE,
        callback=schedule_callback,
        id="agreements.sync",
        description="Synchronize agreements",
        cron="0 * * * *",
    )


@pytest.fixture
def schedule_context(mocker):
    return mocker.Mock(spec=ScheduleContext)


@pytest.fixture
def auth_token(auth_claims_factory, jwt_token_factory):
    return jwt_token_factory(auth_claims_factory(modules={"billing": ["edit"]}))


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def mock_api_service(mocker):
    return mocker.AsyncMock(spec=MPTAPIService)


@pytest.fixture
def api_service_type_factory(mocker):
    def factory(fake_service):
        class FakeAPIService(MPTAPIService):  # noqa: WPS431
            from_auth_context = mocker.AsyncMock(return_value=fake_service)
            from_vendor_account = mocker.AsyncMock(return_value=fake_service)

        fake_service.service_type = FakeAPIService
        return FakeAPIService

    return factory


@pytest.fixture
def api_route_dependencies(mocker, runtime_settings):
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_runtime_settings",
        autospec=True,
        return_value=runtime_settings,
    )
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_extension_settings",
        autospec=True,
        return_value=mocker.sentinel.extension_settings,
    )
