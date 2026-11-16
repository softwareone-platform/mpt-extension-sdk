import dataclasses
from collections.abc import Callable

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind

from mpt_extension_sdk.errors.runtime import ConfigError
from mpt_extension_sdk.observability.bootstrap import ObservabilityBootstrap
from mpt_extension_sdk.observability.config import ObservabilityConfig


@pytest.fixture
def bootstrap_config():
    return ObservabilityConfig(enabled=True, exporters=("otlp",), service_name="svc")


@pytest.fixture
def fastapi_app():
    return FastAPI()


@pytest.fixture
def span_exporter(mocker):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    mocker.patch("opentelemetry.trace.get_tracer_provider", return_value=provider)
    return exporter


@pytest.fixture
def included_routes_app():
    app = FastAPI()
    get_router = APIRouter()
    post_router = APIRouter()
    get_router.add_api_route("/items/{item_id}", lambda item_id: {"get": item_id}, methods=["GET"])
    post_router.add_api_route(
        "/items/{item_id}", lambda item_id: {"post": item_id}, methods=["POST"]
    )
    app.include_router(get_router)
    app.include_router(post_router)
    return app


@pytest.fixture(autouse=True)
def reset_observability_bootstrap_state():
    ObservabilityBootstrap._initialized = False
    ObservabilityBootstrap._fast_api_instrumented = False


@pytest.fixture
def bootstrap_patches(mocker):
    provider = mocker.Mock(spec=["add_span_processor"])
    otlp_exporter = mocker.Mock(spec=Callable)
    batch_processor = mocker.Mock(spec=Callable)
    logging_instrumentor_instance = mocker.Mock(spec=["instrument"])
    httpx_instrumentor_instance = mocker.Mock(spec=["instrument"])

    return {
        "provider": provider,
        "resource_create": mocker.patch(
            "mpt_extension_sdk.observability.bootstrap.Resource.create",
            autospec=True,
            return_value="resource",
        ),
        "tracer_provider": mocker.patch(
            "mpt_extension_sdk.observability.bootstrap.TracerProvider",
            autospec=True,
            return_value=provider,
        ),
        "otlp_span_exporter": mocker.patch(
            "mpt_extension_sdk.observability.bootstrap.OTLPSpanExporter",
            autospec=True,
            return_value=otlp_exporter,
        ),
        "batch_span_processor": mocker.patch(
            "mpt_extension_sdk.observability.bootstrap.BatchSpanProcessor",
            autospec=True,
            return_value=batch_processor,
        ),
        "set_tracer_provider": mocker.patch(
            "mpt_extension_sdk.observability.bootstrap.trace.set_tracer_provider",
            autospec=True,
        ),
        "logging_instrumentor": mocker.patch(
            "mpt_extension_sdk.observability.bootstrap.LoggingInstrumentor",
            autospec=True,
            return_value=logging_instrumentor_instance,
        ),
        "logging_instrumentor_instance": logging_instrumentor_instance,
        "httpx_instrumentor": mocker.patch(
            "mpt_extension_sdk.observability.bootstrap.HTTPXClientInstrumentor",
            autospec=True,
            return_value=httpx_instrumentor_instance,
        ),
        "httpx_instrumentor_instance": httpx_instrumentor_instance,
        "otlp_exporter": otlp_exporter,
        "batch_processor": batch_processor,
    }


def test_observability_config_uses_service_name(runtime_settings):
    result = ObservabilityConfig.from_runtime_settings(runtime_settings)

    assert result.service_name == runtime_settings.otel_service_name


def test_config_without_exporter_destinations(runtime_settings):
    result = ObservabilityConfig.from_runtime_settings(runtime_settings)

    assert result.exporters == ()


def test_config_enables_otlp_when_endpoint_set(runtime_settings):
    settings = dataclasses.replace(runtime_settings, otel_otlp_endpoint="http://jaeger:4318")

    result = ObservabilityConfig.from_runtime_settings(settings)

    assert result.exporters == ("otlp",)


def test_config_enables_azure_when_conn_str_set(runtime_settings):
    settings = dataclasses.replace(
        runtime_settings,
        applicationinsights_connection_string="InstrumentationKey=test",
    )

    result = ObservabilityConfig.from_runtime_settings(settings)

    assert result.exporters == ("azure_monitor",)


def test_config_combines_configured_exporters(runtime_settings):
    settings = dataclasses.replace(
        runtime_settings,
        otel_otlp_endpoint="http://jaeger:4318",
        applicationinsights_connection_string="InstrumentationKey=test",
    )

    result = ObservabilityConfig.from_runtime_settings(settings)

    assert result.exporters == ("otlp", "azure_monitor")


def test_bootstrap_skips_disabled(mocker):
    set_tracer_provider = mocker.patch(
        "mpt_extension_sdk.observability.bootstrap.trace.set_tracer_provider",
        autospec=True,
    )
    config = ObservabilityConfig(enabled=False, exporters=("otlp",), service_name="svc")

    ObservabilityBootstrap.bootstrap(config)  # act

    set_tracer_provider.assert_not_called()


def test_bootstrap_initializes_otlp_once(  # noqa: WPS213
    bootstrap_config, bootstrap_patches
):
    ObservabilityBootstrap.bootstrap(bootstrap_config)

    ObservabilityBootstrap.bootstrap(bootstrap_config)  # act

    bootstrap_patches["resource_create"].assert_called_once_with({"service.name": "svc"})
    bootstrap_patches["tracer_provider"].assert_called_once_with(resource="resource")
    bootstrap_patches["otlp_span_exporter"].assert_called_once_with()
    bootstrap_patches["batch_span_processor"].assert_called_once_with(
        bootstrap_patches["otlp_exporter"]
    )
    bootstrap_patches["provider"].add_span_processor.assert_called_once_with(
        bootstrap_patches["batch_processor"]
    )
    bootstrap_patches["set_tracer_provider"].assert_called_once_with(bootstrap_patches["provider"])
    bootstrap_patches["logging_instrumentor"].assert_called_once_with()
    bootstrap_patches["logging_instrumentor_instance"].instrument.assert_called_once_with(
        set_logging_format=False
    )
    bootstrap_patches["httpx_instrumentor"].assert_called_once_with()
    bootstrap_patches["httpx_instrumentor_instance"].instrument.assert_called_once_with()


def test_bootstrap_rejects_unsupported_exporter(bootstrap_patches):
    config = ObservabilityConfig(enabled=True, exporters=("custom",), service_name="svc")

    with pytest.raises(ConfigError, match="Unsupported OpenTelemetry exporter: custom"):
        ObservabilityBootstrap.bootstrap(config)


def test_bootstrap_rejects_azure_without_conn_str(bootstrap_patches):
    config = ObservabilityConfig(enabled=True, exporters=("azure_monitor",), service_name="svc")

    with pytest.raises(ConfigError, match="applicationinsights_connection_string"):
        ObservabilityBootstrap.bootstrap(config)


def test_bootstrap_rejects_missing_azure_dep(mocker, bootstrap_patches):
    config = ObservabilityConfig(
        enabled=True,
        exporters=("azure_monitor",),
        service_name="svc",
        applicationinsights_connection_string="InstrumentationKey=test",
    )
    mocker.patch(
        "mpt_extension_sdk.observability.bootstrap.importlib.import_module",
        autospec=True,
        side_effect=ModuleNotFoundError,
    )

    with pytest.raises(ConfigError, match="optional dependency"):
        ObservabilityBootstrap.bootstrap(config)


def test_bootstrap_uses_azure_exporter(mocker, bootstrap_patches):
    azure_monitor_trace_exporter = mocker.Mock(spec=Callable, return_value="azure_exporter")
    mocker.patch(
        "mpt_extension_sdk.observability.bootstrap.importlib.import_module",
        autospec=True,
        return_value=type(
            "FakeAzureModule",
            (),
            {"AzureMonitorTraceExporter": azure_monitor_trace_exporter},
        ),
    )
    config = ObservabilityConfig(
        enabled=True,
        exporters=("azure_monitor",),
        service_name="svc",
        applicationinsights_connection_string="InstrumentationKey=test",
    )

    ObservabilityBootstrap.bootstrap(config)  # act

    azure_monitor_trace_exporter.assert_called_once_with(
        connection_string="InstrumentationKey=test"
    )
    bootstrap_patches["batch_span_processor"].assert_called_once_with("azure_exporter")


def test_instrument_fastapi_app_once(mocker, bootstrap_config, fastapi_app):
    instrument_app = mocker.patch(
        "mpt_extension_sdk.observability.bootstrap.FastAPIInstrumentor.instrument_app",
        autospec=True,
    )
    ObservabilityBootstrap.instrument_fastapi_app(fastapi_app, bootstrap_config)

    ObservabilityBootstrap.instrument_fastapi_app(fastapi_app, bootstrap_config)  # act

    instrument_app.assert_called_once_with(fastapi_app)


def test_instrument_fastapi_app_skips_disabled(mocker, fastapi_app):
    instrument_app = mocker.patch(
        "mpt_extension_sdk.observability.bootstrap.FastAPIInstrumentor.instrument_app",
        autospec=True,
    )
    config = ObservabilityConfig(enabled=False, exporters=("otlp",), service_name="svc")

    ObservabilityBootstrap.instrument_fastapi_app(fastapi_app, config)  # act

    instrument_app.assert_not_called()


def test_instrumented_app_routes_by_method(span_exporter, bootstrap_config, included_routes_app):
    ObservabilityBootstrap.instrument_fastapi_app(included_routes_app, bootstrap_config)
    client = TestClient(included_routes_app, raise_server_exceptions=False)

    result = client.post("/items/42")  # act

    assert result.status_code == 200
    assert result.json() == {"post": "42"}


def test_instrumented_app_route_template(span_exporter, bootstrap_config, included_routes_app):
    ObservabilityBootstrap.instrument_fastapi_app(included_routes_app, bootstrap_config)
    client = TestClient(included_routes_app)

    client.get("/items/42")  # act

    server_span = next(
        span for span in span_exporter.get_finished_spans() if span.kind is SpanKind.SERVER
    )
    assert server_span.name == "GET /items/{item_id}"
    assert server_span.attributes["http.route"] == "/items/{item_id}"
