import logging
from functools import wraps

from azure.monitor.opentelemetry.exporter import (
    AzureMonitorTraceExporter,
)
from django.conf import settings
from opentelemetry import trace
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from mpt_extension_sdk.flows.context import Context

logger = logging.getLogger(__name__)


def _response_hook(span, request, response):  # pragma: no cover
    span.set_attribute(
        "request.header.x-correlation-id",
        request.headers.get("x-correlation-id", ""),
    )
    span.set_attribute(
        "request.header.x-request-id",
        request.headers.get("x-request-id", ""),
    )
    if not response.ok:
        span.set_attribute("request.body", request.body or "")
        span.set_attribute("response.body", response.content or "")


def instrument_logging():  # pragma: no cover
    exporter = AzureMonitorTraceExporter(
        connection_string=settings.APPLICATIONINSIGHTS_CONNECTION_STRING
    )

    trace_provider = TracerProvider()
    trace_provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(trace_provider)

    DjangoInstrumentor().instrument()
    RequestsInstrumentor().instrument(response_hook=_response_hook)
    LoggingInstrumentor().instrument(set_logging_format=True)


def wrap_for_trace(func, event_type):  # pragma: no cover
    @wraps(func)
    def opentelemetry_wrapper(client, event):
        tracer = trace.get_tracer(event_type)
        object_id = event.id

        with tracer.start_as_current_span(
            f"Event {event_type} for {object_id}"
        ) as span:
            try:
                func(client, event)
            except Exception:
                logger.exception("Unhandled exception!")
            finally:
                if span.is_recording():
                    span.set_attribute("order.id", object_id)

    @wraps(func)
    def wrapper(client, event):
        try:
            func(client, event)
        except Exception:
            logger.exception("Unhandled exception!")

    return opentelemetry_wrapper if settings.USE_APPLICATIONINSIGHTS else wrapper


def setup_contexts(mpt_client, orders):
    """
    List of contexts from orders
    Args:
        mpt_client (MPTClient): MPT client
        orders (list): List of orders

    Returns: List of contexts

    """
    return [Context(order=order) for order in orders]
