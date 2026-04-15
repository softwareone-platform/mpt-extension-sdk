# flake8: noqa: WPS202
import contextvars
import os
from importlib import import_module
from logging import Filter, Handler, Logger, LogRecord, config, getLogger
from types import ModuleType
from typing import Any, cast, override

from mpt_extension_sdk.errors.runtime import ConfigError

correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)
task_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("task_id", default="")
order_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("order_id", default="")
agreement_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("agreement_id", default="")


def set_event_context(*, task_id: str = "", order_id: str = "", agreement_id: str = "") -> None:
    """Persist entity identifiers for the current event execution."""
    agreement_id_ctx.set(agreement_id)
    order_id_ctx.set(order_id)
    task_id_ctx.set(task_id)


class CorrelationIdFilter(Filter):
    """Injects request-scoped context fields into every log record."""

    @override
    def filter(self, record: LogRecord) -> bool:  # noqa: WPS210
        """Enrich the log record with correlation ID, task ID, and object info.

        Builds a compact `request_context` string for the text formatter and
        sets individual attributes for the JSON formatter.

        Args:
            record: The log record to enrich.

        Returns:
            Always True so the record is not suppressed.
        """
        correlation_id = correlation_id_ctx.get()
        record.correlation_id = correlation_id
        task_id = task_id_ctx.get()
        record.task_id = task_id
        order_id = order_id_ctx.get()
        record.order_id = order_id
        agreement_id = agreement_id_ctx.get()
        record.agreement_id = agreement_id
        trace_id = getattr(record, "otelTraceID", "")
        record.trace_id = trace_id
        record.span_id = getattr(record, "otelSpanID", "")

        parts = [f"({task_id})"] if task_id else []
        if order_id:
            parts.append(f"(order: {order_id})")
        if agreement_id:
            parts.append(f"(agreement: {agreement_id})")
        if trace_id:
            parts.append(f"(trace: {trace_id})")
        record.request_context = " ".join(parts)

        return True


def get_logging_config(log_level: str, ext_package: str | None = None) -> dict[str, Any]:
    """Return a logging configuration dictionary compatible with dictConfig.

    Args:
        log_level: Root log level string (e.g. `"INFO"`, `"DEBUG"`).
        ext_package: The name of the extension package.

    Returns:
        A dict ready to pass to `logging.config.dictConfig`.
    """
    formatter_config = {
        "format": "{asctime} {name} {levelname} (pid: {process}) {request_context} {message}",
        "style": "{",
    }

    loggers = {
        "mpt_extension_sdk": {
            "handlers": ["console"],
            "level": log_level,
            "propagate": False,
        },
    }
    if ext_package:
        loggers[ext_package] = {
            "handlers": ["console"],
            "level": log_level,
            "propagate": False,
        }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "correlation_id": {
                "()": "mpt_extension_sdk.runtime.logging.CorrelationIdFilter",
            },
        },
        "formatters": {
            "verbose": formatter_config,
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "filters": ["correlation_id"],
                "stream": "ext://sys.stderr",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "WARNING",
        },
        "loggers": loggers,
    }


def get_azure_monitor_handler() -> Handler | None:
    """Return an optional Azure Monitor log handler when configured."""
    if os.getenv("SDK_OBSERVABILITY_ENABLED", "true").lower() not in {"true", "1", "yes"}:
        return None

    connection_string = _get_azure_connection_string()
    if connection_string is None:
        return None

    dependencies = _load_azure_monitor_dependencies()
    if dependencies is None:
        raise ConfigError(
            "Azure Monitor logging is configured, but required Azure/OpenTelemetry "
            "logging dependencies are not installed"
        )

    return _build_azure_monitor_handler(
        connection_string=connection_string, dependencies=dependencies
    )


def setup_logging(log_level: str = "INFO", ext_package: str | None = None) -> None:
    """Initialize process-wide logging.

    Args:
        log_level: Root log level string. Defaults to `"INFO"`.
        ext_package: The name of the extension package.
    """
    config.dictConfig(get_logging_config(log_level=log_level, ext_package=ext_package))
    azure_handler = get_azure_monitor_handler()
    if azure_handler is None:
        return

    azure_handler.addFilter(CorrelationIdFilter())
    _attach_handler_once(getLogger(), azure_handler)
    _attach_handler_once(getLogger("mpt_extension_sdk"), azure_handler)
    if ext_package:
        _attach_handler_once(getLogger(ext_package), azure_handler)


def _resolve_logging_service_name() -> str:
    """Return the service name used by the optional Azure log exporter."""
    configured = os.getenv("SDK_OTEL_SERVICE_NAME", "")
    if configured:
        return configured

    raise ConfigError("SDK_OTEL_SERVICE_NAME is required when SDK_OBSERVABILITY_ENABLED is enabled")


def _get_azure_connection_string() -> str | None:
    """Return the configured Azure Monitor connection string when available."""
    connection_string = os.getenv("SDK_APPLICATIONINSIGHTS_CONNECTION_STRING", "")
    if not connection_string:
        return None

    return connection_string


def _load_azure_monitor_dependencies() -> (
    tuple[ModuleType, ModuleType, ModuleType, ModuleType] | None
):
    """Load Azure and OpenTelemetry modules required to build the logging handler."""
    try:  # noqa: WPS229
        azure_exporter_module = import_module("azure.monitor.opentelemetry.exporter")
        resources_module = import_module("opentelemetry.sdk.resources")
    except ModuleNotFoundError:
        return None

    logs_module, logs_export_module = _load_opentelemetry_log_modules()
    if logs_module is None or logs_export_module is None:
        return None

    return azure_exporter_module, resources_module, logs_module, logs_export_module


def _build_azure_monitor_handler(
    *, connection_string: str, dependencies: tuple[ModuleType, ModuleType, ModuleType, ModuleType]
) -> Handler:
    """Build the Azure Monitor logging handler from loaded modules and config."""
    azure_exporter_module, resources_module, logs_module, logs_export_module = dependencies
    logger_provider = _build_azure_logger_provider(
        connection_string=connection_string,
        azure_exporter_module=azure_exporter_module,
        resources_module=resources_module,
        logs_export_module=logs_export_module,
        logs_module=logs_module,
    )
    return cast(Handler, logs_module.LoggingHandler(level=0, logger_provider=logger_provider))


def _build_azure_logger_provider(
    *,
    connection_string: str,
    azure_exporter_module: ModuleType,
    resources_module: ModuleType,
    logs_export_module: ModuleType,
    logs_module: ModuleType,
) -> Any:
    """Create and configure the OpenTelemetry logger provider for Azure Monitor."""
    logger_provider = logs_module.LoggerProvider(
        resource=resources_module.Resource.create(
            {"service.name": _resolve_logging_service_name()},
        ),
    )
    logger_provider.add_log_record_processor(
        logs_export_module.BatchLogRecordProcessor(
            azure_exporter_module.AzureMonitorLogExporter(connection_string=connection_string)
        )
    )
    return logger_provider


def _load_opentelemetry_log_modules() -> tuple[ModuleType | None, ModuleType | None]:
    """Load log SDK modules, preferring public paths when the installed version exposes them."""
    module_names = (
        ("opentelemetry.sdk.logs", "opentelemetry.sdk.logs.export"),
        ("opentelemetry.sdk._logs", "opentelemetry.sdk._logs.export"),
    )
    for logs_module_name, export_module_name in module_names:
        try:
            modules = import_module(logs_module_name), import_module(export_module_name)
        except ModuleNotFoundError:
            modules = None

        if modules is not None:
            return modules

    return None, None


def _attach_handler_once(logger: Logger, log_handler: Handler) -> None:
    """Attach a handler only if an equivalent handler has not been added yet."""
    handler_type = type(log_handler)
    if any(isinstance(existing, handler_type) for existing in logger.handlers):
        return
    logger.addHandler(log_handler)
