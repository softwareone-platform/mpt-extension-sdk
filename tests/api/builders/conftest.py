import datetime as dt
from collections.abc import Callable

import pytest

from mpt_extension_sdk.models.task import Task
from mpt_extension_sdk.pipeline import ScheduleContext
from mpt_extension_sdk.routing import RouteType, ScheduleRouteDefinition
from mpt_extension_sdk.runtime.async_tasks import AsyncTaskRunner
from mpt_extension_sdk.services.mpt_api_service.task import TaskService


@pytest.fixture
def task_factory():
    def factory(status, *, created_seconds_ago=0, started_seconds_ago=None):
        now = dt.datetime.now(dt.UTC)
        created_at = now - dt.timedelta(seconds=created_seconds_ago)
        audit = {"created": {"at": created_at.isoformat()}}
        if started_seconds_ago is not None:
            started_at = now - dt.timedelta(seconds=started_seconds_ago)
            audit["started"] = {"at": started_at.isoformat()}
        return Task(id="TSK-001", status=status, audit=audit)

    return factory


@pytest.fixture
def task_service(mocker, task_factory):
    service = mocker.AsyncMock(spec=TaskService)
    service.get.return_value = task_factory("Queued")
    return service


@pytest.fixture
def async_task_runner(mocker):
    runner = mocker.MagicMock(spec=AsyncTaskRunner)
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
