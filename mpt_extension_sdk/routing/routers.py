from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.extension_validator import ExtensionValidator
from mpt_extension_sdk.routing.models import (
    APIRouteDefinition,
    BaseRouteDefinition,
    EventDeliveryMode,
    EventRouteDefinition,
    PlugRouteDefinition,
    RouteCallback,
    RouteType,
    ScheduleRouteDefinition,
)

_NO_CONTEXT_ADAPTER = object()


@dataclass
class BaseExtensionRouter:
    """Shared router behavior for extension route families."""

    prefix: str = ""
    _routes: list[BaseRouteDefinition] = field(default_factory=list, init=False, repr=False)

    @property
    def routes(self) -> list[BaseRouteDefinition]:
        """Return the registered route definitions."""
        return list(self._routes)

    def prefixed_routes(self, prefix: str) -> list[BaseRouteDefinition]:
        """Return route definitions with the given prefix applied to each path."""
        return [self._with_prefix(prefix, route) for route in self._routes]

    def _join_paths(self, prefix: str, path: str) -> str:
        """Join a router prefix and route path."""
        base = path.strip()
        if not base:
            raise ValueError("Route path cannot be empty")

        suffix = base if base.startswith("/") else f"/{base}"
        cleaned_prefix = prefix.strip()
        if not cleaned_prefix:
            return suffix

        normalized_prefix = (
            cleaned_prefix if cleaned_prefix.startswith("/") else f"/{cleaned_prefix}"
        )
        normalized_prefix = normalized_prefix.rstrip("/")
        if not normalized_prefix:
            return suffix

        return normalized_prefix if suffix == "/" else f"{normalized_prefix}{suffix}"

    def _with_prefix(self, prefix: str, route: BaseRouteDefinition) -> BaseRouteDefinition:
        """Return a copy of the route with the provided prefix applied."""
        route_payload = {**route.__dict__}
        route_payload["path"] = self._join_paths(prefix, route.path)
        return type(route)(**route_payload)

    def _register_base_route(self, route: BaseRouteDefinition) -> None:
        """Register a route definition on the router."""
        if not route.name.strip():
            raise ValueError("Route name cannot be empty")

        ExtensionValidator.validate_route_uniqueness(route=route, routes=self._routes)
        self._routes.append(route)


@dataclass
class EventRouter(BaseExtensionRouter):
    """Router object for event handlers."""

    context_adapter_type: type[ContextAdapter] | None = None

    def __post_init__(self) -> None:
        """Validate the default router adapter when configured."""
        ExtensionValidator.validate_context_adapter_type(self.context_adapter_type)

    def event(
        self,
        path: str,
        name: str,
        event: str,
        condition: str | None = None,
        context_adapter_type: type[ContextAdapter] | object | None = _NO_CONTEXT_ADAPTER,
    ) -> Callable[[RouteCallback], RouteCallback]:
        """Register a non-task event handler on the router."""
        return self._create_event_decorator(
            definition_payload={
                "path": path,
                "name": name,
                "event": event,
                "condition": condition,
                "delivery_mode": EventDeliveryMode.EVENT,
                "context_adapter_type": (
                    self.context_adapter_type
                    if context_adapter_type is _NO_CONTEXT_ADAPTER
                    else context_adapter_type
                ),
            }
        )

    def task(
        self,
        path: str,
        name: str,
        event: str,
        condition: str | None = None,
        context_adapter_type: type[ContextAdapter] | object | None = _NO_CONTEXT_ADAPTER,
    ) -> Callable[[RouteCallback], RouteCallback]:
        """Register a task-based event handler on the router."""
        return self._create_event_decorator(
            definition_payload={
                "path": path,
                "name": name,
                "event": event,
                "condition": condition,
                "delivery_mode": EventDeliveryMode.TASK,
                "context_adapter_type": (
                    self.context_adapter_type
                    if context_adapter_type is _NO_CONTEXT_ADAPTER
                    else context_adapter_type
                ),
            }
        )

    def _create_event_decorator(
        self, *, definition_payload: dict[str, object]
    ) -> Callable[[RouteCallback], RouteCallback]:
        event = cast(str, definition_payload["event"])
        if not event.strip():
            raise ValueError("Route event cannot be empty")
        resolved_adapter_type = cast(
            "type[ContextAdapter] | None", definition_payload["context_adapter_type"]
        )
        ExtensionValidator.validate_context_adapter_type(resolved_adapter_type)
        normalized_path = self._join_paths(self.prefix, cast(str, definition_payload["path"]))

        def decorator(event_handler: RouteCallback) -> RouteCallback:
            self._register_base_route(
                EventRouteDefinition(
                    name=cast(str, definition_payload["name"]),
                    path=normalized_path,
                    route_type=RouteType.EVENT,
                    callback=event_handler,
                    event=event,
                    delivery_mode=cast(EventDeliveryMode, definition_payload["delivery_mode"]),
                    condition=cast(str | None, definition_payload["condition"]),
                    context_adapter_type=resolved_adapter_type,
                )
            )
            return event_handler

        return decorator


@dataclass
class APIRouter(BaseExtensionRouter):
    """Router object for authenticated API endpoints."""

    def endpoint(self, path: str, name: str) -> Callable[[RouteCallback], RouteCallback]:
        """Register an authenticated API handler."""
        normalized_path = self._join_paths(self.prefix, path)

        def decorator(route_handler: RouteCallback) -> RouteCallback:
            self._register_base_route(
                APIRouteDefinition(
                    name=name,
                    path=normalized_path,
                    route_type=RouteType.API,
                    callback=route_handler,
                )
            )
            return route_handler

        return decorator


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
