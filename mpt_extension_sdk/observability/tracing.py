from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from opentelemetry.trace import Span, SpanKind, get_tracer

TRACER = get_tracer("mpt_extension_sdk")
type AttributeValue = str | int | float | bool
type Attributes = dict[str, AttributeValue]


@dataclass(frozen=True, kw_only=True)
class RouteSpanAttributes:
    """Common route span attributes."""

    route_type: str
    route_path: str
    route_name: str | None = None
    method: str | None = None
    account_id: str | None = None
    extension_id: str | None = None
    correlation_id: str | None = None
    task_based: bool | None = None

    def to_dict(self) -> Attributes:
        """Return sanitized OpenTelemetry attributes."""
        attributes: Attributes = {
            "mpt.extension.route_type": self.route_type,
            "mpt.extension.route_path": self.route_path,
        }
        optional_attributes: dict[str, AttributeValue | None] = {
            "mpt.extension.route_name": self.route_name,
            "http.request.method": self.method,
            "mpt.account.id": self.account_id,
            "mpt.extension.id": self.extension_id,
            "mpt.correlation_id": self.correlation_id,
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
def start_event_span(path: str, *, task_based: bool, event: Any) -> Iterator[Span]:  # noqa: WPS210
    """Start and yield the span for an incoming event delivery."""
    object_type = getattr(getattr(event, "object", None), "object_type", "")
    object_id = getattr(getattr(event, "object", None), "id", "")
    event_type = getattr(getattr(event, "details", None), "event_type", "")
    business_attributes: Attributes = {}
    if object_type == "Order" and object_id:
        business_attributes["order.id"] = object_id
    if object_type == "Agreement" and object_id:
        business_attributes["agreement.id"] = object_id
    span_name = _build_event_span_name(object_type, object_id)
    with TRACER.start_as_current_span(span_name, kind=SpanKind.INTERNAL) as span:
        route_attributes = RouteSpanAttributes(
            route_type="event",
            route_path=path,
            task_based=task_based,
        )
        set_attributes(
            span,
            {
                **route_attributes.to_dict(),
                "mpt.event.id": getattr(event, "id", ""),
                "mpt.event.type": event_type,
                "mpt.task.id": getattr(getattr(event, "task", None), "id", ""),
                **business_attributes,
            },
        )
        yield span


@contextmanager
def start_api_span(  # noqa: WPS211
    *,
    route_name: str,
    route_path: str,
    method: str,
    account_id: str,
    extension_id: str,
    correlation_id: str,
) -> Iterator[Span]:
    """Start and yield the span for an authenticated API request."""
    with TRACER.start_as_current_span(f"API {method} {route_path}", kind=SpanKind.INTERNAL) as span:
        route_attributes = RouteSpanAttributes(
            route_type="api",
            route_name=route_name,
            route_path=route_path,
            method=method,
            account_id=account_id,
            extension_id=extension_id,
            correlation_id=correlation_id,
        )
        set_attributes(span, route_attributes.to_dict())
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
