from collections.abc import Callable
from dataclasses import dataclass

from mpt_extension_sdk.routing.enums import RouteType
from mpt_extension_sdk.routing.models import ScheduleRouteDefinition
from mpt_extension_sdk.routing.routers.base import BaseExtensionRouter
from mpt_extension_sdk.routing.types import RouteCallback


@dataclass
class ScheduleRouter(BaseExtensionRouter):
    """Router object for schedule handlers."""

    def schedule(self, path: str, name: str) -> Callable[[RouteCallback], RouteCallback]:
        """Register a schedule handler."""
        normalized_path = self._join_paths(self.prefix, path)

        def decorator(route_handler: RouteCallback) -> RouteCallback:
            self._register_base_route(
                ScheduleRouteDefinition(
                    name=name,
                    path=normalized_path,
                    route_type=RouteType.SCHEDULE,
                    callback=route_handler,
                )
            )
            return route_handler

        return decorator
