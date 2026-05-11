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
| `LOG_LEVEL` | `INFO` | `DEBUG` | Default runtime log level |
| `SDK_OBSERVABILITY_ENABLED` | `true` | `false` | Enables SDK observability bootstrap |
| `SDK_APPLICATIONINSIGHTS_CONNECTION_STRING` | - | `InstrumentationKey=...` | Azure Monitor connection string used by the SDK observability bootstrap |
| `SDK_OTEL_SERVICE_NAME` | - | `my-extension` | Optional OpenTelemetry service name override |
| `SDK_OTEL_EXPORTERS` | SDK default | `otlp` | Demo/runtime exporter selection for the SDK observability bootstrap |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | exporter default | `http://jaeger:4318` | OTLP collector endpoint used when OTLP export is enabled |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | exporter default | `http/protobuf` | OTLP protocol for the configured exporter |

The demo environment files may also include integration-specific variables such
as `MPT_PORTAL_BASE_URL`. Those are example application settings for the
mock/demo setup rather than core SDK runtime requirements.

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

## Runtime Notes

- [`mpt_extension_sdk/settings/runtime.py`](../mpt_extension_sdk/settings/runtime.py)
  loads runtime configuration from environment variables and auto-discovers the
  extension package.
- `RuntimeSettings` validates `SDK_EXTENSION_URL`, `SDK_EXTENSION_API_KEY`,
  `SDK_EXTENSION_ID`, and `MPT_API_BASE_URL` as required
  environment variables.
- [`mpt_extension_sdk/runtime/runner.py`](../mpt_extension_sdk/runtime/runner.py)
  writes `meta.yaml` before startup and selects Uvicorn or Ziticorn depending
  on the CLI mode.
- In local `FastAPI + uvicorn` mode, `SDK_LOCAL_RELOAD=true` takes precedence
  over multi-worker settings. Use reload for local development, or disable
  reload before increasing `SDK_LOCAL_WORKERS`.
- [`mpt_extension_sdk/runtime/bootstrap/registration.py`](../mpt_extension_sdk/runtime/bootstrap/registration.py)
  registers the running extension instance and persists the returned identity
  when present.

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
- OTLP exporting by default
- Azure Monitor exporting when `SDK_APPLICATIONINSIGHTS_CONNECTION_STRING` is set

OpenTelemetry exporter-specific variables such as
`OTEL_EXPORTER_OTLP_ENDPOINT` are read by the underlying OpenTelemetry
exporter, not by `RuntimeSettings` directly.

Document additional repository-specific configuration here when SDK runtime
requirements expand.
