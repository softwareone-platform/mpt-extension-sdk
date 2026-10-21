import pytest

from mpt_extension_sdk.routing import (
    ModalPlug,
    NavigationPlug,
    Plug,
    PlugRouteDefinition,
    RouteType,
    TaskTimeouts,
)
from mpt_extension_sdk.runtime.builders import MetaConfigBuilder, PlugMetadataBuilder


def test_plug_metadata_builder_reuse(mocker):
    plug_provider = mocker.Mock(
        return_value=[
            Plug(
                id="adobe",
                name="Adobe",
                description="Adobe widget",
                socket="commerce.agreements.agreement",
                href="main-menu.js",
            )
        ]
    )
    plug_metadata_builder = PlugMetadataBuilder(
        routes=[
            PlugRouteDefinition(
                name="plug-provider",
                path="/plug-provider",
                route_type=RouteType.PLUG,
                callback=plug_provider,
            )
        ]
    )
    first_result = plug_metadata_builder.build()

    result = plug_metadata_builder.build()  # act

    assert first_result == result


def test_builder_emits_navigation_plug_no_href(mocker):
    plug_provider = mocker.Mock(
        return_value=[
            NavigationPlug(id="learn-extensions", name="Learn Extensions", socket="portal")
        ]
    )
    plug_metadata_builder = PlugMetadataBuilder(
        routes=[
            PlugRouteDefinition(
                name="plug-provider",
                path="/plug-provider",
                route_type=RouteType.PLUG,
                callback=plug_provider,
            )
        ]
    )

    result = plug_metadata_builder.build()

    assert result[0].model_dump(exclude_none=True) == {
        "id": "learn-extensions",
        "name": "Learn Extensions",
        "socket": "portal",
    }


def test_builder_emits_modal_plug_no_socket(mocker):
    plug_provider = mocker.Mock(
        return_value=[
            ModalPlug(
                id="confirm-dialog",
                name="Confirm Dialog",
                description="Confirmation dialog",
                href="dialogs/confirm.js",
            )
        ]
    )
    plug_metadata_builder = PlugMetadataBuilder(
        routes=[
            PlugRouteDefinition(
                name="plug-provider",
                path="/plug-provider",
                route_type=RouteType.PLUG,
                callback=plug_provider,
            )
        ]
    )

    result = plug_metadata_builder.build()

    assert result[0].model_dump(exclude_none=True) == {
        "id": "confirm-dialog",
        "name": "Confirm Dialog",
        "description": "Confirmation dialog",
        "href": "/static/dialogs/confirm.js",
    }


def test_builder_rejects_duplicate_modal_plug_id(mocker):
    plug_provider = mocker.Mock(
        return_value=[
            ModalPlug(id="adobe", name="Adobe Dialog", href="dialog.js"),
            Plug(
                id="adobe",
                name="Adobe",
                description="Adobe widget",
                socket="portal.adobe",
                href="main-menu.js",
            ),
        ]
    )
    plug_metadata_builder = PlugMetadataBuilder(
        routes=[
            PlugRouteDefinition(
                name="plug-provider",
                path="/plug-provider",
                route_type=RouteType.PLUG,
                callback=plug_provider,
            )
        ]
    )

    with pytest.raises(ValueError, match="Plug id 'adobe' is already registered"):
        plug_metadata_builder.build()


def test_builder_rejects_duplicate_id_mixed_types(mocker):
    plug_provider = mocker.Mock(
        return_value=[
            NavigationPlug(id="adobe", name="Adobe Group", socket="portal"),
            Plug(
                id="adobe",
                name="Adobe",
                description="Adobe widget",
                socket="portal.adobe",
                href="main-menu.js",
            ),
        ]
    )
    plug_metadata_builder = PlugMetadataBuilder(
        routes=[
            PlugRouteDefinition(
                name="plug-provider",
                path="/plug-provider",
                route_type=RouteType.PLUG,
                callback=plug_provider,
            )
        ]
    )

    with pytest.raises(ValueError, match="Plug id 'adobe' is already registered"):
        plug_metadata_builder.build()


@pytest.mark.parametrize(
    ("timeouts", "expected_timeouts"),
    [
        (None, None),
        (TaskTimeouts(max_task_lifespan=7200), {"maxTaskLifespan": 7200}),
        (
            TaskTimeouts(max_task_lifespan=7200, max_task_processing=3600),
            {"maxTaskLifespan": 7200, "maxTaskProcessing": 3600},
        ),
    ],
)
def test_builder_emits_deferrable(api_route_factory, timeouts, expected_timeouts):
    route = api_route_factory(path="/api/v2/agreements/sync/", deferrable=True, timeouts=timeouts)
    expected = {"path": "/api/v2/agreements/sync/", "method": "POST"}
    if expected_timeouts is not None:
        expected["timeouts"] = expected_timeouts

    result = MetaConfigBuilder(openapi="/openapi.json", routes=[route]).build()

    assert result.model_dump(exclude_none=True, by_alias=True)["deferrables"] == [expected]


def test_builder_omits_empty_deferrables(api_route_factory):
    route = api_route_factory(path="/api/v2/agreements")

    result = MetaConfigBuilder(openapi="/openapi.json", routes=[route]).build()

    assert "deferrables" not in result.model_dump(exclude_none=True, by_alias=True)
