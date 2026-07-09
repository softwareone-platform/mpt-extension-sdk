import pytest

from mpt_extension_sdk.routing import NavigationPlug, Plug, PlugRouteDefinition, RouteType
from mpt_extension_sdk.runtime.builders import PlugMetadataBuilder


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
