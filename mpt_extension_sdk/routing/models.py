from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.routing.enums import EventDeliveryMode, HTTPMethod, RouteType
from mpt_extension_sdk.schemas import BaseSchema

RouteCallback = Callable[..., Awaitable[object] | object]


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

    method: HTTPMethod = HTTPMethod.GET
    body_validator_type: type[BaseSchema] | None = None


@dataclass(frozen=True)
class ScheduleRouteDefinition(BaseRouteDefinition):
    """Route definition for schedule handlers."""


@dataclass(frozen=True)
class PlugRouteDefinition(BaseRouteDefinition):
    """Route definition for plug handlers."""
