from collections.abc import Callable

import pytest

from mpt_extension_sdk.routing import RouteType, ScheduleRouteDefinition
from mpt_extension_sdk.routing.validators import RouteValidator


@pytest.fixture
def schedule_route(mocker):
    def factory(name, path, schedule_id):
        return ScheduleRouteDefinition(
            name=name,
            path=path,
            route_type=RouteType.SCHEDULE,
            callback=mocker.Mock(spec=Callable),
            id=schedule_id,
            description="Sync data",
            cron="0 0 * * *",
        )

    return factory


def test_validate_rejects_duplicate_schedule_id(schedule_route):
    existing = schedule_route("first", "/schedule/first", "sync")
    duplicate = schedule_route("second", "/schedule/second", "sync")

    with pytest.raises(ValueError, match="Schedule id 'sync' is already registered"):
        RouteValidator.validate_route_uniqueness(route=duplicate, routes=[existing])
