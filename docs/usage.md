# SDK Usage

This guide is the entry point for building an extension package on top of
`mpt-extension-sdk`. Topic-specific examples live in smaller documents under
[`sdk_usage/`](sdk_usage/).

## Usage Topics

- [Application setup](sdk_usage/application.md): install the SDK, shape an
  extension package, create `ExtensionApp`, include routers, and configure the
  runtime.
- [Event routes](sdk_usage/events.md): register task and non-task event handlers
  (and the status of schedule routes).
- [Authenticated API routes](sdk_usage/api.md): expose authenticated endpoints,
  validate bodies, read request/auth context, return API responses, and use
  pagination.
- [UI plugs](sdk_usage/plugs.md): register `PlugRouter` providers, group plugs
  under nested navigation containers, declare modal (open-by-id) plugs, and
  reference static assets.
- [Contexts and pipelines](sdk_usage/contexts-and-pipelines.md): adapt execution
  contexts, compose pipelines, drive the step lifecycle and flow control, use
  pipeline hooks, and declare status transitions.
- [Immutable snapshots](sdk_usage/immutable-snapshots.md): treat MPT models as
  immutable, update parameters with the `with_*` helpers, and refresh after a
  write.
- [Error handling](sdk_usage/error-handling.md): raise typed step/pipeline
  errors and let the SDK map them to event responses.
- [Settings](sdk_usage/settings.md): the runtime, extension, and account
  settings layers and the environment-variable helpers.
- [Observability](sdk_usage/observability.md): SDK tracing, the
  `azure-monitor` extra, and extension-defined spans with `trace_span`.
- [CLI and metadata](sdk_usage/cli.md): the `mpt-ext` commands and `meta.yaml`
  generation/validation.
- [Marketplace services](sdk_usage/marketplace-services.md): use
  `ctx.mpt_api_service` from handlers and pipeline steps.

## Runtime Commands

Use the `mpt-ext` CLI command when running an extension built on top of the SDK:

```bash
mpt-ext run --local
mpt-ext run
mpt-ext meta generate
mpt-ext meta validate
```

- `mpt-ext run --local` starts the local `FastAPI + uvicorn` runtime.
- `mpt-ext run` writes `meta.yaml`, registers the extension instance, and starts
  the platform runtime with `mrok`/`ziticorn`.
- `mpt-ext meta generate` writes metadata derived from `ext_app.to_meta_config()`.
- `mpt-ext meta validate` compares the checked-in `meta.yaml` with generated
  metadata, validates plug static assets, and writes `meta.generated.yaml` when
  validation fails.
