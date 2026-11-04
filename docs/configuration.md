# Configuration

This document describes repository-specific runtime configuration exposed by the SDK.

## Core Environment Variables

The SDK runtime relies on these settings:

| Variable | Default | Example | Description |
| --- | --- | --- | --- |
| `SDK_EXTENSION_URL` | - | `https://extensions.example.com` | Extension registration endpoint used during platform startup |
| `SDK_EXTENSION_API_KEY` | - | `eyJhbGciOi...` | API key used for extension registration and runtime task operations |
| `SDK_EXTENSION_ID` | - | `EXT-1234` | Extension identifier used during instance registration |
| `SDK_EXTENSION_EXTERNAL_ID` | host-derived | `dev-laptop-01` | Stable external id for the running extension instance |
| `SDK_IDENTITY_FILE_PATH` | `<cwd>/<external_id>_identity.json` | `/tmp/ext_identity.json` | Path where the Ziticorn identity file is stored or loaded |
| `MPT_API_BASE_URL` | - | `https://api.s1.show` | SoftwareONE Marketplace API base URL |
| `SDK_LOCAL_HOST` | `0.0.0.0` | `127.0.0.1` | Host used by the local Uvicorn runtime |
| `SDK_LOCAL_PORT` | `8080` | `8081` | Port used by the local Uvicorn runtime |
| `SDK_LOCAL_RELOAD` | `true` | `false` | Enables Uvicorn reload mode for local development |
| `SDK_LOCAL_WORKERS` | `1` | `2` | Worker count for local Uvicorn mode |
| `SDK_ZITI_WORKERS` | `4` | `8` | Worker count for Ziticorn platform runtime |
| `SDK_ZITI_RELOAD` | `false` | `true` | Enables Ziticorn reload mode |
| `SDK_MAX_CONCURRENT_TASKS` | unbounded | `10` | Maximum task executions, schedule, task-backed event and deferred together, that each worker process runs at the same time; `0` runs none |
| `LOG_LEVEL` | `INFO` | `DEBUG` | Default runtime log level |
| `SDK_OBSERVABILITY_ENABLED` | `true` | `false` | Enables SDK observability bootstrap |
| `SDK_APPLICATIONINSIGHTS_CONNECTION_STRING` | - | `InstrumentationKey=...` | Azure Monitor connection string used by the SDK observability bootstrap |
| `SDK_OTEL_SERVICE_NAME` | - | `my-extension` | Optional OpenTelemetry service name override |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | - | `http://jaeger:4318` | OTLP collector endpoint; setting it enables the OTLP exporter |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | exporter default | `http/protobuf` | OTLP protocol for the configured exporter |

The standard traces-specific variable `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`
can be used instead; when set, it also enables the OTLP exporter and takes
precedence over `OTEL_EXPORTER_OTLP_ENDPOINT`.

## Runtime Discovery

The runtime discovers the extension package automatically from the current
working directory. It expects exactly one top-level package that exports:

- `app.py` with `ext_app`
- `settings.py` with `ExtensionSettings`

`ExtensionSettings` must inherit from
`mpt_extension_sdk.settings.extension.BaseExtensionSettings`.

The runtime then derives:

- `app_module` as `<package>.app`
- `settings_module` as `<package>.settings`
- `meta.yaml` from `ext_app.to_meta_config()`

## Example Environment

```dotenv
SDK_EXTENSION_URL=https://extensions.example.com
SDK_EXTENSION_API_KEY=<extension-api-key>
SDK_EXTENSION_ID=EXT-1234
SDK_EXTENSION_EXTERNAL_ID=local-dev
MPT_API_BASE_URL=https://api.s1.show
SDK_LOCAL_HOST=0.0.0.0
SDK_LOCAL_PORT=8080
LOG_LEVEL=INFO
```

## Setting Rules

- `SDK_EXTENSION_URL`, `SDK_EXTENSION_API_KEY`, `SDK_EXTENSION_ID`, and
  `MPT_API_BASE_URL` are required; the runtime settings fail to load without
  them.
- `SDK_LOCAL_RELOAD=true` takes precedence over `SDK_LOCAL_WORKERS`. Disable
  reload before increasing the local worker count.
- `SDK_MAX_CONCURRENT_TASKS` applies to each worker process on its own, so an
  instance runs up to that value times its worker count; `0` stops the process
  from running any task. A negative or non-integer value raises `ConfigError`
  when the runtime settings load. How a delivery at the limit is answered is
  described in [sdk_usage/tasks.md](sdk_usage/tasks.md#delivery-protocol).
- `SDK_EXTENSION_INSTANCE_ID` is set by the SDK, not by the deployment: any
  inherited value is cleared, and it is only set in platform mode when
  registration returns an instance id (see
  [sdk_usage/cli.md](sdk_usage/cli.md#running-the-extension)).
- With `SDK_ZITI_RELOAD=true`, every reloaded worker registers the instance
  again, so plug, event, and schedule metadata changes reach the platform
  without a full restart. Use it only for development.

## Observability

Observability is configured through the SDK runtime settings. A typical setup
includes:

```bash
SDK_OBSERVABILITY_ENABLED=true
SDK_APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
SDK_OTEL_SERVICE_NAME=my-extension
```

When observability is enabled, the SDK bootstraps:

- FastAPI instrumentation
- HTTPX client instrumentation
- logging correlation through OpenTelemetry logging instrumentation
- OTLP exporting when `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` or
  `OTEL_EXPORTER_OTLP_ENDPOINT` is set
- Azure Monitor exporting when `SDK_APPLICATIONINSIGHTS_CONNECTION_STRING` is set

The SDK reads the OTLP endpoint variables only to decide whether the OTLP
exporter is enabled. Their values, together with other exporter-specific
variables such as `OTEL_EXPORTER_OTLP_PROTOCOL`, are consumed by the
underlying OpenTelemetry exporter, not by `RuntimeSettings` directly.

Document additional repository-specific configuration here when SDK runtime
requirements expand.
