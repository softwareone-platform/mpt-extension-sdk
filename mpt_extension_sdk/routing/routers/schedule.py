from collections.abc import Callable
from dataclasses import dataclass

from mpt_extension_sdk.routing.enums import RouteType
from mpt_extension_sdk.routing.models import ScheduleRouteDefinition
from mpt_extension_sdk.routing.routers.base import BaseExtensionRouter
from mpt_extension_sdk.routing.types import ScheduleRouteCallback


@dataclass
class ScheduleRouter(BaseExtensionRouter):
    """Router object for schedule handlers."""

    def task(
        self,
        path: str,
        *,
        id: str,  # ruff:ignore[builtin-argument-shadowing] - metadata contract uses "id"
        name: str,
        description: str,
        cron: str,
    ) -> Callable[[ScheduleRouteCallback], ScheduleRouteCallback]:
        """Register a scheduled task."""
        normalized_path = self._join_paths(self.prefix, path)

        def decorator(route_handler: ScheduleRouteCallback) -> ScheduleRouteCallback:
            self._register_base_route(
                ScheduleRouteDefinition(
                    name=name,
                    path=normalized_path,
                    route_type=RouteType.SCHEDULE,
                    callback=route_handler,
                    id=id,
                    description=description,
                    cron=cron,
                )
            )
            return route_handler

        return decorator
