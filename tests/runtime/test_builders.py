from mpt_extension_sdk.routing import Plug, PlugRouteDefinition, RouteType
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
