from dataclasses import dataclass

from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.routing.decorators import is_only_deferrable
from mpt_extension_sdk.routing.enums import EventDeliveryMode, HTTPMethod, RouteType
from mpt_extension_sdk.routing.types import (
    APIRouteCallback,
    EventRouteCallback,
    PlugRouteCallback,
    RouteCallback,
    ScheduleRouteCallback,
)
from mpt_extension_sdk.schemas import BaseSchema


@dataclass(frozen=True)
class TaskTimeouts:
    """Task lifetime limits a deferrable API route declares, in seconds."""

    max_task_lifespan: int | None = None
    max_task_processing: int | None = None

    def __post_init__(self) -> None:
        """Reject a declaration that carries no limit."""
        if self.max_task_lifespan is None and self.max_task_processing is None:
            raise ValueError(
                "Task timeouts must declare max_task_lifespan, max_task_processing or both"
            )


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

    callback: EventRouteCallback
    event: str
    delivery_mode: EventDeliveryMode
    condition: str | None = None
    context_adapter_type: type[ContextAdapter] | None = None


@dataclass(frozen=True)
class APIRouteDefinition(BaseRouteDefinition):
    """Route definition for authenticated API endpoints."""

    callback: APIRouteCallback
    method: HTTPMethod = HTTPMethod.GET
    body_validator_type: type[BaseSchema] | None = None
    deferrable: bool = False
    timeouts: TaskTimeouts | None = None

    def __post_init__(self) -> None:
        """Reject an only-deferrable handler on a route that is not deferrable."""
        if self.only_deferrable and not self.deferrable:
            raise TypeError(
                f"Route '{self.path}' has an only-deferrable handler but is not deferrable: "
                "set deferrable=True"
            )

    @property
    def only_deferrable(self) -> bool:
        """Whether the handler is restricted to deferred delivery."""
        return is_only_deferrable(self.callback)


@dataclass(frozen=True)
class ScheduleRouteDefinition(BaseRouteDefinition):
    """Route definition for schedule handlers."""

    callback: ScheduleRouteCallback
    id: str
    description: str
    cron: str


@dataclass(frozen=True)
class PlugRouteDefinition(BaseRouteDefinition):
    """Route definition for plug handlers."""

    callback: PlugRouteCallback
