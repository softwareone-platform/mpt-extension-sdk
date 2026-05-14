from collections.abc import Callable
from dataclasses import dataclass

from mpt_extension_sdk.routing.enums import RouteType
from mpt_extension_sdk.routing.models import PlugRouteDefinition
from mpt_extension_sdk.routing.routers.base import BaseExtensionRouter
from mpt_extension_sdk.routing.types import RouteCallback


@dataclass
class PlugRouter(BaseExtensionRouter):
    """Router object for static plug handlers."""

    def plug(self, path: str, name: str) -> Callable[[RouteCallback], RouteCallback]:
        """Register a plug handler."""
        normalized_path = self._join_paths(self.prefix, path)

        def decorator(route_handler: RouteCallback) -> RouteCallback:
            self._register_base_route(
                PlugRouteDefinition(
                    name=name,
                    path=normalized_path,
                    route_type=RouteType.PLUG,
                    callback=route_handler,
                )
            )
            return route_handler

        return decorator
