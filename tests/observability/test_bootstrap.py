from collections.abc import Callable

import pytest
from fastapi import FastAPI

from mpt_extension_sdk.errors.runtime import ConfigError
from mpt_extension_sdk.observability.bootstrap import ObservabilityBootstrap
from mpt_extension_sdk.observability.config import ObservabilityConfig


@pytest.fixture
def bootstrap_config():
    return ObservabilityConfig(enabled=True, exporters=("otlp",), service_name="svc")


@pytest.fixture
def fastapi_app():
    return FastAPI()


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
