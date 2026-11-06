import pytest

from mpt_extension_sdk.routing import RouteType, ScheduleRouter


def test_schedule_router_registers_task(async_route_handler):
    router = ScheduleRouter(prefix="/schedule")

    result = router.task(
        path="daily",
        id="daily-sync",
        name="Daily Sync",
        description="Sync data every day",
        cron="0 0 * * *",
    )(async_route_handler)

    assert result is async_route_handler
    assert len(router.routes) == 1
    route = router.routes[0]
    assert (
        route.path,
        route.name,
        route.id,
        route.description,
        route.cron,
        route.route_type,
    ) == (
        "/schedule/daily",
        "Daily Sync",
        "daily-sync",
        "Sync data every day",
        "0 0 * * *",
        RouteType.SCHEDULE,
    )


def test_schedule_router_rejects_sync_handler(route_handler):
    router = ScheduleRouter(prefix="/schedule")
    route_handler.__qualname__ = "sync_agreements"

    with pytest.raises(TypeError, match="'sync_agreements' must be a coroutine function"):
        router.task(
            path="daily",
            id="daily-sync",
            name="Daily Sync",
            description="Sync data every day",
            cron="0 0 * * *",
        )(route_handler)
