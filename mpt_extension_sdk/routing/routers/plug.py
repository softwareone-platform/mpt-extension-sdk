from collections.abc import Callable
from dataclasses import dataclass

from mpt_extension_sdk.routing.enums import RouteType
from mpt_extension_sdk.routing.models import PlugRouteDefinition
from mpt_extension_sdk.routing.routers.base import BaseExtensionRouter
from mpt_extension_sdk.routing.types import PlugRouteCallback


@dataclass
class PlugRouter(BaseExtensionRouter):
    """Router object for static plug handlers."""

    def register(self) -> Callable[[PlugRouteCallback], PlugRouteCallback]:
        """Register a plug metadata provider."""

        def decorator(plug_provider: PlugRouteCallback) -> PlugRouteCallback:
            self._register_base_route(
                PlugRouteDefinition(
                    name=plug_provider.__name__,
                    path=self._join_paths(self.prefix, plug_provider.__name__),
                    route_type=RouteType.PLUG,
                    callback=plug_provider,
                )
            )
            return plug_provider

        return decorator
