from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.extension_validator import ExtensionValidator
from mpt_extension_sdk.routing.enums import EventDeliveryMode, RouteType
from mpt_extension_sdk.routing.models import EventRouteDefinition
from mpt_extension_sdk.routing.routers.base import BaseExtensionRouter
from mpt_extension_sdk.routing.types import EventRouteCallback

_NO_CONTEXT_ADAPTER = object()


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
    ) -> Callable[[EventRouteCallback], EventRouteCallback]:
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
    ) -> Callable[[EventRouteCallback], EventRouteCallback]:
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
    ) -> Callable[[EventRouteCallback], EventRouteCallback]:
        event = cast(str, definition_payload["event"])
        if not event.strip():
            raise ValueError("Route event cannot be empty")
        resolved_adapter_type = cast(
            "type[ContextAdapter] | None", definition_payload["context_adapter_type"]
        )
        ExtensionValidator.validate_context_adapter_type(resolved_adapter_type)
        normalized_path = self._join_paths(self.prefix, cast(str, definition_payload["path"]))

        def decorator(event_handler: EventRouteCallback) -> EventRouteCallback:
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
