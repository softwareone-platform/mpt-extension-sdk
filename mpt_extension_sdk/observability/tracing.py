from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self

from opentelemetry.trace import Span, SpanKind, get_tracer

from mpt_extension_sdk.api.models.events import EventObjectType
from mpt_extension_sdk.runtime.logging import correlation_id_ctx

if TYPE_CHECKING:
    from mpt_extension_sdk.api.auth import AuthContext
    from mpt_extension_sdk.routing.models import BaseRouteDefinition

TRACER = get_tracer("mpt_extension_sdk")
type AttributeValue = str | int | float | bool
type Attributes = dict[str, AttributeValue]


@dataclass(frozen=True, kw_only=True)
class RouteSpanAttributes:
    """Common route span attributes."""

    route_path: str
    route_type: str
    account_id: str | None = None
    correlation_id: str | None = None
    extension_id: str | None = None
    method: str | None = None
    route_name: str | None = None
    task_based: bool | None = None

    @classmethod
    def from_route(
        cls,
        route: "BaseRouteDefinition",
        auth_context: "AuthContext",
        *,
        method: str | None = None,
    ) -> Self:
        """Return the attributes of an authenticated route call."""
        return cls(
            account_id=auth_context.account.id,
            correlation_id=correlation_id_ctx.get(),
            extension_id=auth_context.extension_id,
            method=method,
            route_name=route.name,
            route_path=route.path,
            route_type=route.route_type,
        )

    def to_dict(self) -> Attributes:
        """Return sanitized OpenTelemetry attributes."""
        attributes: Attributes = {
            "mpt.extension.route_path": self.route_path,
            "mpt.extension.route_type": self.route_type,
        }
        optional_attributes: dict[str, AttributeValue | None] = {
            "http.request.method": self.method,
            "mpt.account.id": self.account_id,
            "mpt.correlation_id": self.correlation_id,
            "mpt.extension.id": self.extension_id,
            "mpt.extension.route_name": self.route_name,
            "mpt.extension.task_based": self.task_based,
        }
        return {
            **attributes,
            **{
                key: attribute
                for key, attribute in optional_attributes.items()
                if attribute is not None
            },
        }


@contextmanager
def start_event_span(path: str, *, task_based: bool, event: Any) -> Generator[Span]:
    """Start and yield the span for an incoming event delivery."""
    object_type = getattr(getattr(event, "object", None), "object_type", "")
    object_id = getattr(getattr(event, "object", None), "id", "")
    business_attributes: Attributes = {}
    if object_type == EventObjectType.ORDER and object_id:
        business_attributes["order.id"] = object_id
    if object_type == EventObjectType.AGREEMENT and object_id:
        business_attributes["agreement.id"] = object_id
    with start_route_span(
        _build_event_span_name(object_type, object_id),
        RouteSpanAttributes(route_path=path, route_type="event", task_based=task_based),
        {
            "mpt.event.id": getattr(event, "id", ""),
            "mpt.event.type": getattr(getattr(event, "details", None), "event_type", ""),
            "mpt.task.id": getattr(getattr(event, "task", None), "id", ""),
            **business_attributes,
        },
    ) as span:
        yield span


@contextmanager
def start_route_span(
    span_name: str,
    route_attributes: RouteSpanAttributes,
    attributes: Attributes | None = None,
) -> Generator[Span]:
    """Start and yield the span of a route call.

    Args:
        span_name: Name of the span.
        route_attributes: Attributes every route span carries.
        attributes: Attributes of the route family, such as the event or webhook type.
    """
    with TRACER.start_as_current_span(span_name, kind=SpanKind.INTERNAL) as span:
        set_attributes(span, {**route_attributes.to_dict(), **(attributes or {})})
        yield span


def record_exception(span: Span, error: Exception) -> None:
    """Record an exception on the provided span."""
    span.record_exception(error)


def set_attributes(span: Span, attributes: Attributes) -> None:
    """Apply sanitized attributes to a span."""
    for key, att_value in attributes.items():
        if isinstance(att_value, bool | str | int | float):
            span.set_attribute(key, att_value)


def get_business_attributes(ctx: Any) -> Attributes:
    """Return business dimensions for the current agreement/order context."""
    attributes: Attributes = {}
    if getattr(ctx, "order", None) is not None:
        attributes["order.id"] = ctx.order.id
        return attributes
    if getattr(ctx, "agreement", None) is not None:
        attributes["agreement.id"] = ctx.agreement.id
    return attributes


def _build_event_span_name(object_type: str, object_id: str) -> str:
    """Return a human-readable root span name for AppInsights transaction views."""
    normalized_type = object_type.lower()
    if normalized_type == "order" and object_id:
        return f"Event order for {object_id}"
    if normalized_type == "agreement" and object_id:
        return f"Process agreement {object_id}"

    return f"Event {normalized_type}"
