from collections.abc import Callable

import pytest

from mpt_extension_sdk.routing import Plug, PlugRouter, RouteType


def test_plug_normalizes_static_asset_paths():
    result = Plug(
        id="adobe",
        name="Adobe",
        description="Adobe widget",
        icon="assets/adobe.png",
        socket="commerce.agreements.agreement",
        href="/static/main-menu.js",
    )

    assert result.icon == "/static/assets/adobe.png"
    assert result.href == "/static/main-menu.js"


def test_plug_rejects_path_traversal():
    with pytest.raises(
        ValueError, match="Plug static asset path must stay under the static folder"
    ):
        Plug(
            id="adobe",
            name="Adobe",
            description="Adobe widget",
            socket="commerce.agreements.agreement",
            href="../main-menu.js",
        )


@pytest.mark.parametrize("href", ["/static", "/static/"])
def test_plug_rejects_static_root_path(href):
    with pytest.raises(ValueError, match="Plug static asset path must include a file"):
        Plug(
            id="adobe",
            name="Adobe",
            description="Adobe widget",
            socket="commerce.agreements.agreement",
            href=href,
        )


def test_plug_router_registers_provider(mocker):
    router = PlugRouter(prefix="/plug")
    plug_provider = mocker.Mock(
        return_value=Plug(
            id="adobe",
            name="Adobe",
            description="Adobe widget",
            socket="commerce.agreements.agreement",
            href="main-menu.js",
        ),
        spec=Callable,
        __name__="plug_provider",
    )

    result = router.register()(plug_provider)

    assert len(router.routes) == 1
    assert result is plug_provider
    route = router.routes[0]
    assert (route.path, route.name, route.route_type) == (
        "/plug/plug_provider",
        "plug_provider",
        RouteType.PLUG,
    )
    assert route.callback() == plug_provider()
