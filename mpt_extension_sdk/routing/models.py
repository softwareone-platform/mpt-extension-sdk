from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum

from mpt_extension_sdk.context import ContextAdapter

RouteCallback = Callable[..., Awaitable[None] | None]


class RouteType(StrEnum):
    """Supported route families."""

    EVENT = "event"
    API = "api"
    SCHEDULE = "schedule"
    PLUG = "plug"


class EventDeliveryMode(StrEnum):
    """Supported event delivery modes."""

    EVENT = "event"
    TASK = "task"


@dataclass(frozen=True)
class BaseRouteDefinition:
    """Base route definition owned by an extension application."""

    name: str
    path: str
    route_type: RouteType
    callback: RouteCallback


@dataclass(frozen=True)
class EventRouteDefinition(BaseRouteDefinition):
    """Route definition for Marketplace events."""

    event: str
    delivery_mode: EventDeliveryMode
    condition: str | None = None
    context_adapter_type: type[ContextAdapter] | None = None


@dataclass(frozen=True)
class APIRouteDefinition(BaseRouteDefinition):
    """Route definition for authenticated API endpoints."""


@dataclass(frozen=True)
class ScheduleRouteDefinition(BaseRouteDefinition):
    """Route definition for schedule handlers."""


@dataclass(frozen=True)
class PlugRouteDefinition(BaseRouteDefinition):
    """Route definition for plug handlers."""
