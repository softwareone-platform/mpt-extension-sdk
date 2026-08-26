# Observability

The SDK owns tracing for the runtime and for pipeline execution. The baseline
instrumentation (the tracing provider, FastAPI/`httpx`/logging hooks, and the
pipeline and step spans) is wired through SDK hooks and middleware, so handlers,
pipelines, and steps do not set up manual OpenTelemetry instrumentation
themselves. Business code can still add its own child spans through the
SDK-provided `trace_span` decorator (see below).

## What The SDK Instruments

When observability is enabled, the SDK bootstrap:

- configures the process-wide `TracerProvider`
- instruments the FastAPI app (inbound HTTP spans)
- instruments `httpx` (outbound HTTP client spans)
- instruments logging correlation, adding `trace_id` and `span_id` to log records

On top of the standard HTTP spans, the SDK emits its own spans for pipeline and
step execution:

- pipeline spans named `pipeline: <PipelineName>`
- step spans named `step: <StepName>`

Both are enriched with event and business correlation attributes, including
`mpt.event.id`, `mpt.task.id`, and the main business identifier (such as
`order.id` or `agreement.id`).

## Configuration

Observability is controlled through runtime environment variables (see
[configuration.md](../configuration.md)):

- `SDK_OBSERVABILITY_ENABLED` enables or disables the bootstrap (default `true`).
- `SDK_OTEL_SERVICE_NAME` overrides the reported service name.
- `SDK_APPLICATIONINSIGHTS_CONNECTION_STRING` enables the Azure Monitor exporter
  when set.
- `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` or `OTEL_EXPORTER_OTLP_ENDPOINT` enables
  the OTLP exporter when set.

Each exporter is activated only when its destination configuration is present:
the OTLP exporter when an OTLP endpoint variable is set, and the Azure Monitor
exporter when the Application Insights connection string is set. When neither
is configured, the tracer provider runs without exporters, so instrumentation
stays active without export noise. The Azure Monitor exporter requires the
optional dependency:

```bash
pip install "mpt-extension-sdk[azure-monitor]"
```

If the connection string is set but the optional dependency is missing, the SDK
raises `ConfigError` with installation guidance.

## Extension-Defined Spans

The SDK creates a parent span around each route execution and propagates the
active tracing context into the handler, so extension code can add child spans
for business-specific operations. Use the `trace_span` decorator:

```python
from mpt_extension_sdk.observability import trace_span


class AgreementSync:
    @trace_span("adobe.sync_agreements")
    async def execute(self, ctx) -> None:
        agreements = await ctx.mpt_api_service.agreements.get_all()
        for agreement in agreements:
            await self.sync_agreement(ctx, agreement)

    @trace_span(
        "adobe.sync_agreement",
        attributes={
            "agreement.id": lambda self, ctx, agreement: agreement.id,
        },
    )
    async def sync_agreement(self, ctx, agreement) -> None: ...
```

The first argument is the stable operation name shown in the trace tree.
`attributes` add request-specific values for filtering and diagnostics; each
value is either a static scalar or a callable evaluated from the decorated
function's arguments. Only `bool`, `str`, `int`, and `float` results are
recorded, and attribute resolution failures are skipped without breaking the
call. `trace_span` works on both async and sync functions.

## Adding Other Instrumentation

If an extension needs additional dependency-specific instrumentation, register it
through `ExtensionApp.on_startup` in the same `app.py` module where
`ExtensionApp` is created — not inside handlers, pipelines, or steps:

```python
from mpt_extension_sdk import ExtensionApp
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor

ext_app = ExtensionApp(prefix="/api/v2")


@ext_app.on_startup
def instrument_dependencies() -> None:
    """Register extra instrumentation once the runtime starts serving."""
    BotocoreInstrumentor().instrument()
```

Startup hooks run only when the runtime serves the extension (`mpt-ext run`),
after the SDK has configured the tracer provider and before the app reports
itself as ready, so extra instrumentation attaches to the same provider the SDK
bootstraps. Metadata generation (`mpt-ext meta generate` / `meta validate`)
never invokes startup hooks, so instrumentation registered this way stays out of
metadata runs and `app.py` keeps a deterministic import.

See [application.md](application.md#run-code-at-runtime-startup) for the general
startup-hook contract.
