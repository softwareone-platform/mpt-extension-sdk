from typing import NamedTuple

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from mpt_extension_sdk.observability import tracing

PATH = "/api/v2/events/orders/change"


class FakeSpanRunResult(NamedTuple):
    current_span: object
    related_span: object


class FakeEventSpanRunner:
    def __init__(self, exporter, tracer):
        self.exporter = exporter
        self.tracer = tracer

    def __call__(self, *, event, task_based, span_name):
        parent_context = self.tracer.start_as_current_span("request-span")
        event_context = tracing.start_event_span(PATH, task_based=task_based, event=event)

        with parent_context, event_context:
            current_span = trace.get_current_span()

        related_span = next(
            span for span in self.exporter.get_finished_spans() if span.name == span_name
        )
        return FakeSpanRunResult(current_span=current_span, related_span=related_span)


@pytest.fixture
def span_exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider.get_tracer("tests")


@pytest.fixture
def event_span_runner(mocker, span_exporter):
    exporter, tracer = span_exporter
    mocker.patch.object(tracing, "TRACER", tracer)
    return FakeEventSpanRunner(exporter=exporter, tracer=tracer)


def test_event_span_keeps_parent(event_factory, event_span_runner):
    result = event_span_runner(
        event=event_factory(),
        task_based=False,
        span_name="request-span",
    )

    assert result.current_span.parent is not None
    assert result.current_span.parent.span_id == result.related_span.context.span_id


def test_event_span_sets_attributes(event_factory, event_span_runner):
    result = event_span_runner(
        event=event_factory(),
        task_based=True,
        span_name="Event order for ORD-1111-1112",
    )

    assert result.related_span.attributes["mpt.extension.route_path"] == PATH
    assert result.related_span.attributes["mpt.extension.task_based"] is True
    assert result.related_span.attributes["mpt.event.id"] == "EVT-1111-1112"
    assert result.related_span.attributes["mpt.event.type"] == "OrderPurchased"
    assert result.related_span.attributes["order.id"] == "ORD-1111-1112"
