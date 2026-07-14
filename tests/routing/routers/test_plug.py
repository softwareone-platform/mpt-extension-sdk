from collections.abc import Callable

import pytest

from mpt_extension_sdk.routing import NavigationPlug, Plug, PlugRouter, RouteType


@pytest.fixture
def list_plug_provider() -> Callable[[], list[Plug]]:
    def factory() -> list[Plug]:
        return [
            Plug(
                id="adobe",
                name="Adobe",
                description="Adobe widget",
                socket="commerce.agreements.agreement",
                href="main-menu.js",
            )
        ]

    return factory


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


def test_navigation_plug_normalizes_icon_path():
    result = NavigationPlug(
        id="learn-extensions",
        name="Learn Extensions",
        socket="portal",
        description="Learning resources",
        icon="assets/learn.png",
    )

    assert result.icon == "/static/assets/learn.png"
    assert result.description == "Learning resources"


def test_navigation_plug_derives_nested_socket():
    result = NavigationPlug(id="learn-extensions", name="Learn Extensions", socket="portal")

    assert result.nested_socket == "portal.learn-extensions"


def test_navigation_plug_strips_id_and_socket():
    result = NavigationPlug(id=" learn-extensions ", name="Learn Extensions", socket=" portal ")

    assert (result.id, result.socket) == ("learn-extensions", "portal")
    assert result.nested_socket == "portal.learn-extensions"


@pytest.mark.parametrize("field_name", ["id", "name", "socket"])
def test_navigation_plug_rejects_empty_fields(field_name):
    plug_fields = {"id": "learn-extensions", "name": "Learn Extensions", "socket": "portal"}
    plug_fields[field_name] = "  "

    with pytest.raises(ValueError, match=f"Navigation plug {field_name} cannot be empty"):
        NavigationPlug(**plug_fields)


def test_navigation_plug_blank_description_fails():
    with pytest.raises(ValueError, match="Navigation plug description cannot be empty"):
        NavigationPlug(
            id="learn-extensions",
            name="Learn Extensions",
            socket="portal",
            description=" ",
        )


def test_navigation_plug_rejects_href():
    plug_fields = {
        "id": "learn-extensions",
        "name": "Learn Extensions",
        "socket": "portal",
        "href": "main-menu.js",
    }

    with pytest.raises(TypeError, match="unexpected keyword argument 'href'"):
        NavigationPlug(**plug_fields)


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


def test_plug_router_accepts_list_plug_provider(list_plug_provider: Callable[[], list[Plug]]):
    router = PlugRouter(prefix="/plug")

    result = router.register()(list_plug_provider)  # act

    assert result is list_plug_provider
    assert router.routes[0].callback() == list_plug_provider()
