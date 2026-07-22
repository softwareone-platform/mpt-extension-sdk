import logging

import pytest

from mpt_extension_sdk.errors.runtime import ConfigError
from mpt_extension_sdk.models.task import UnknownTaskStatusWarning
from mpt_extension_sdk.runtime import logging as runtime_logging


@pytest.fixture
def azure_monitor_mocks(mocker):
    return {
        "resource_create": mocker.Mock(),
        "logger_provider": mocker.Mock(),
        "logging_handler": mocker.Mock(),
        "batch_processor": mocker.Mock(),
        "azure_exporter": mocker.Mock(),
    }


@pytest.fixture
def azure_monitor_modules(mocker, azure_monitor_mocks):
    exporter_mod = mocker.Mock()
    exporter_mod.AzureMonitorLogExporter = azure_monitor_mocks["azure_exporter"]

    resources_mod = mocker.Mock()
    resources_mod.Resource.create = azure_monitor_mocks["resource_create"]

    logs_mod = mocker.Mock()
    logs_mod.LoggerProvider = azure_monitor_mocks["logger_provider"]
    logs_mod.LoggingHandler = azure_monitor_mocks["logging_handler"]

    logs_export_mod = mocker.Mock()
    logs_export_mod.BatchLogRecordProcessor = azure_monitor_mocks["batch_processor"]

    modules = {
        "azure.monitor.opentelemetry.exporter": exporter_mod,
        "opentelemetry.sdk.resources": resources_mod,
        "opentelemetry.sdk.logs": logs_mod,
        "opentelemetry.sdk.logs.export": logs_export_mod,
    }

    return {"modules": modules, **azure_monitor_mocks}


@pytest.fixture
def patch_logging_imports(mocker, azure_monitor_modules):
    return mocker.patch(
        "mpt_extension_sdk.runtime.logging.import_module",
        autospec=True,
        side_effect=lambda module_name: azure_monitor_modules["modules"][module_name],
    )


@pytest.fixture(autouse=True)
def reset_logging_context():
    runtime_logging.correlation_id_ctx.set("")
    runtime_logging.set_event_context()
    yield
    runtime_logging.correlation_id_ctx.set("")
    runtime_logging.set_event_context()


def test_get_azure_handler_requires_service_name(
    mocker, azure_monitor_modules, patch_logging_imports
):
    mocker.patch.dict(
        "os.environ",
        {
            "SDK_OBSERVABILITY_ENABLED": "true",
            "SDK_APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test",
            "SDK_OTEL_SERVICE_NAME": "",
        },
    )

    with pytest.raises(ConfigError):
        runtime_logging.get_azure_monitor_handler()

    azure_monitor_modules["resource_create"].assert_not_called()
    azure_monitor_modules["logger_provider"].assert_not_called()
    azure_monitor_modules["logging_handler"].assert_not_called()
    azure_monitor_modules["batch_processor"].assert_not_called()
    azure_monitor_modules["azure_exporter"].assert_not_called()


def test_set_event_context_updates_context_vars():
    runtime_logging.set_event_context(
        task_id="TASK-1", order_id="ORD-1", agreement_id="AGR-1"
    )  # act

    assert runtime_logging.task_id_ctx.get() == "TASK-1"
    assert runtime_logging.order_id_ctx.get() == "ORD-1"
    assert runtime_logging.agreement_id_ctx.get() == "AGR-1"


def test_correlation_id_filter_sets_record_fields():  # noqa: WPS218
    runtime_logging.correlation_id_ctx.set("corr-1")
    runtime_logging.set_event_context(task_id="TASK-1", order_id="ORD-1", agreement_id="AGR-1")
    record = logging.LogRecord("tests", logging.INFO, __file__, 10, "msg", (), None)
    record.otelTraceID = "trace-1"
    record.otelSpanID = "span-1"

    result = runtime_logging.CorrelationIdFilter().filter(record)

    assert result is True
    assert record.correlation_id == "corr-1"
    assert record.task_id == "TASK-1"
    assert record.order_id == "ORD-1"
    assert record.agreement_id == "AGR-1"
    assert record.trace_id == "trace-1"
    assert record.span_id == "span-1"
    assert record.request_context == ("(TASK-1) (order: ORD-1) (agreement: AGR-1) (trace: trace-1)")


def test_filter_without_optional_data():
    runtime_logging.correlation_id_ctx.set("corr-2")
    runtime_logging.set_event_context()
    record = logging.LogRecord("tests", logging.INFO, __file__, 10, "msg", (), None)

    result = runtime_logging.CorrelationIdFilter().filter(record)

    assert result is True
    assert (
        record.correlation_id,
        record.task_id,
        record.order_id,
        record.agreement_id,
        record.trace_id,
        record.span_id,
        record.request_context,
    ) == ("corr-2", "", "", "", "", "", "")


def test_get_logging_config_includes_ext_logger():
    result = runtime_logging.get_logging_config("DEBUG", ext_package="mock_extension")

    assert result["loggers"]["mpt_extension_sdk"]["level"] == "DEBUG"
    assert result["loggers"]["mock_extension"]["handlers"] == ["console"]


def test_get_logging_config_without_ext_logger():
    result = runtime_logging.get_logging_config("INFO")

    assert result["root"]["level"] == "WARNING"
    assert "mpt_extension_sdk" in result["loggers"]
    assert "mock_extension" not in result["loggers"]


def test_get_azure_observability_disabled(mocker):
    mocker.patch.dict(
        "os.environ",
        {
            "SDK_OBSERVABILITY_ENABLED": "false",
            "SDK_APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test",
        },
    )

    result = runtime_logging.get_azure_monitor_handler()

    assert result is None


def test_get_azure_handler_without_env(mocker):
    mocker.patch.dict(
        "os.environ",
        {
            "SDK_OBSERVABILITY_ENABLED": "true",
            "SDK_APPLICATIONINSIGHTS_CONNECTION_STRING": "",
        },
    )

    result = runtime_logging.get_azure_monitor_handler()

    assert result is None


def test_get_azure_handler_without_dependencies(mocker):
    mocker.patch.dict(
        "os.environ",
        {
            "SDK_OBSERVABILITY_ENABLED": "true",
            "SDK_APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test",
            "SDK_OTEL_SERVICE_NAME": "svc",
        },
    )
    mocker.patch(
        "mpt_extension_sdk.runtime.logging.import_module",
        autospec=True,
        side_effect=ModuleNotFoundError,
    )

    with pytest.raises(ConfigError, match="logging dependencies are not installed"):
        runtime_logging.get_azure_monitor_handler()


def test_get_azure_handler_builds_logging_handler(
    mocker, azure_monitor_modules, patch_logging_imports
):
    mocker.patch.dict(
        "os.environ",
        {
            "SDK_OBSERVABILITY_ENABLED": "true",
            "SDK_APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test",
            "SDK_OTEL_SERVICE_NAME": "svc",
        },
    )

    result = runtime_logging.get_azure_monitor_handler()

    assert result is azure_monitor_modules["logging_handler"].return_value
    azure_monitor_modules["resource_create"].assert_called_once_with({"service.name": "svc"})
    azure_monitor_modules["logger_provider"].assert_called_once_with(resource=mocker.ANY)
    azure_monitor_modules["azure_exporter"].assert_called_once_with(
        connection_string="InstrumentationKey=test"
    )
    azure_monitor_modules["batch_processor"].assert_called_once_with(
        azure_monitor_modules["azure_exporter"].return_value
    )
    azure_monitor_modules[
        "logger_provider"
    ].return_value.add_log_record_processor.assert_called_once_with(
        azure_monitor_modules["batch_processor"].return_value
    )
    azure_monitor_modules["logging_handler"].assert_called_once_with(
        level=0,
        logger_provider=azure_monitor_modules["logger_provider"].return_value,
    )


def test_setup_logging_attaches_azure_handler(mocker):
    dict_config = mocker.patch("mpt_extension_sdk.runtime.logging.config.dictConfig", autospec=True)
    azure_handler = mocker.Mock(spec=logging.Handler)
    get_azure_handler = mocker.patch(
        "mpt_extension_sdk.runtime.logging.get_azure_monitor_handler",
        autospec=True,
        return_value=azure_handler,
    )
    attach_handler_once = mocker.patch(
        "mpt_extension_sdk.runtime.logging._attach_handler_once",
        autospec=True,
    )

    runtime_logging.setup_logging(log_level="INFO", ext_package="mock_extension")  # act

    dict_config.assert_called_once()
    get_azure_handler.assert_called_once_with()
    azure_handler.addFilter.assert_called_once()
    assert attach_handler_once.call_count == 3


def test_setup_logging_captures_warnings(mocker):
    mocker.patch("mpt_extension_sdk.runtime.logging.config.dictConfig", autospec=True)
    mocker.patch(
        "mpt_extension_sdk.runtime.logging.get_azure_monitor_handler",
        autospec=True,
        return_value=None,
    )
    capture_warnings = mocker.patch(
        "mpt_extension_sdk.runtime.logging.logging.captureWarnings", autospec=True
    )
    filter_warnings = mocker.patch(
        "mpt_extension_sdk.runtime.logging.warnings.filterwarnings", autospec=True
    )

    runtime_logging.setup_logging(log_level="INFO", ext_package="mock_extension")  # act

    capture_warnings.assert_called_once_with(True)  # ruff:ignore[boolean-positional-value-in-call]
    filter_warnings.assert_called_once_with("always", category=UnknownTaskStatusWarning)


def test_setup_logging_skips_azure_attach(mocker):
    dict_config = mocker.patch("mpt_extension_sdk.runtime.logging.config.dictConfig", autospec=True)
    get_azure_handler = mocker.patch(
        "mpt_extension_sdk.runtime.logging.get_azure_monitor_handler",
        autospec=True,
        return_value=None,
    )
    attach_handler_once = mocker.patch(
        "mpt_extension_sdk.runtime.logging._attach_handler_once",
        autospec=True,
    )

    runtime_logging.setup_logging(log_level="INFO", ext_package="mock_extension")  # act

    dict_config.assert_called_once()
    get_azure_handler.assert_called_once_with()
    attach_handler_once.assert_not_called()
