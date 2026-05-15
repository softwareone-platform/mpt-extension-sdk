from mpt_extension_sdk.routing import RouteType, ScheduleRouter


def test_schedule_router_registers_handler(route_handler):
    router = ScheduleRouter(prefix="/schedule")

    result = router.schedule(path="daily", name="daily-sync")(route_handler)

    assert result is route_handler
    assert len(router.routes) == 1
    route = router.routes[0]
    assert route.path == "/schedule/daily"
    assert route.name == "daily-sync"
    assert route.route_type == RouteType.SCHEDULE
