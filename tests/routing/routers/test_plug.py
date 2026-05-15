from mpt_extension_sdk.routing import PlugRouter, RouteType


def test_plug_router_registers_handler(route_handler):
    router = PlugRouter(prefix="/plug")

    result = router.plug(path="assets", name="assets")(route_handler)

    assert result is route_handler
    assert len(router.routes) == 1
    route = router.routes[0]
    assert route.path == "/plug/assets"
    assert route.name == "assets"
    assert route.route_type == RouteType.PLUG
