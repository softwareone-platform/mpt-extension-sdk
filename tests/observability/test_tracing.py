import asyncio
from operator import itemgetter
from typing import NamedTuple

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from mpt_extension_sdk.observability import decorators, trace_span, tracing

PATH = "/api/v2/events/orders/change"


@trace_span(
    "adobe.sync_agreement",
    attributes={
        "agreement.id": itemgetter("id"),
        "sync.retry": 1,
        "sync.enabled": True,
        "sync.ignored": None,
    },
)
async def trace_sample_async(agreement):
    await asyncio.sleep(0)
    return agreement["id"]


@trace_span("adobe.build_payload")
def trace_sample_sync():
    return {"ok": True}


@trace_span(
    "adobe.sync_with_missing_attr",
    attributes={
        "agreement.id": itemgetter("id"),
        "agreement.missing": itemgetter("missing"),
    },
)
async def trace_sample_missing_attr(agreement):
    await asyncio.sleep(0)
    return agreement["id"]


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


def test_trace_span_wraps_async_attrs(mocker, span_exporter):
    exporter, tracer = span_exporter
    mocker.patch.object(decorators, "TRACER", tracer)

    result = asyncio.run(trace_sample_async({"id": "AGR-1"}))

    span = next(
        finished_span
        for finished_span in exporter.get_finished_spans()
        if finished_span.name == "adobe.sync_agreement"
    )
    assert result == "AGR-1"
    assert span.attributes["agreement.id"] == "AGR-1"
    assert span.attributes["sync.retry"] == 1
    assert span.attributes["sync.enabled"] is True
    assert "sync.ignored" not in span.attributes


def test_trace_span_wraps_sync_function(mocker, span_exporter):
    exporter, tracer = span_exporter
    mocker.patch.object(decorators, "TRACER", tracer)

    result = trace_sample_sync()

    span = next(
        finished_span
        for finished_span in exporter.get_finished_spans()
        if finished_span.name == "adobe.build_payload"
    )
    assert result == {"ok": True}
    assert span.name == "adobe.build_payload"


def test_trace_span_omits_failing_callable_attr(mocker, span_exporter):
    exporter, tracer = span_exporter
    mocker.patch.object(decorators, "TRACER", tracer)

    result = asyncio.run(trace_sample_missing_attr({"id": "AGR-2"}))

    span = next(
        finished_span
        for finished_span in exporter.get_finished_spans()
        if finished_span.name == "adobe.sync_with_missing_attr"
    )
    assert result == "AGR-2"
    assert span.attributes["agreement.id"] == "AGR-2"
    assert "agreement.missing" not in span.attributes


def test_event_span_sets_agreement_attributes(event_factory, event_span_runner):
    result = event_span_runner(
        event=event_factory(object_type="Agreement", object_id="AGR-1111-1112"),
        task_based=False,
        span_name="Process agreement AGR-1111-1112",
    )

    assert result.related_span.attributes["agreement.id"] == "AGR-1111-1112"
    assert result.related_span.attributes["mpt.extension.route_type"] == "event"


def test_event_span_uses_generic_name(event_factory, event_span_runner):
    result = event_span_runner(
        event=event_factory(object_type="Asset", object_id="AST-1111-1112"),
        task_based=False,
        span_name="Event asset",
    )

    assert result.related_span.name == "Event asset"


def test_business_attributes_return_agreement_id(agreement_factory):
    ctx = type("Context", (), {"agreement": agreement_factory(), "order": None})()

    result = tracing.get_business_attributes(ctx)

    assert result == {"agreement.id": "AGR-1111-1112"}


def test_business_attributes_return_order_id(order_factory):
    ctx = type("Context", (), {"agreement": None, "order": order_factory()})()

    result = tracing.get_business_attributes(ctx)

    assert result == {"order.id": "ORD-1111-1112"}


def test_business_attributes_return_empty():
    ctx = type("Context", (), {"agreement": None, "order": None})()

    result = tracing.get_business_attributes(ctx)

    assert not result
