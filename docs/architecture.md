# Architecture

This document describes repository-specific structure for the SoftwareONE Extension SDK.

## Repository Role

`mpt-extension-sdk` is a shared library repository. It provides reusable building blocks for SoftwareONE Marketplace extensions rather than a single business-specific extension service.

The repository combines:

- public SDK primitives for defining an extension application, route registration, and typed handler context
- runtime wiring for FastAPI request handling, local startup with `uvicorn`, and platform startup with `mrok`/`ziticorn`
- Marketplace service helpers, settings discovery, observability instrumentation, and metadata generation
- local tooling for Docker-based development, validation, and packaging

## Public SDK Concepts

The main extension authoring concepts are:

- `ExtensionApp`: the root SDK object for one extension package; it includes routers, applies route context adapters, generates metadata, and runs startup hooks
- route-family routers: `EventRouter`, `APIRouter`, `ScheduleRouter`, and `WebhookRouter` register handlers under a shared prefix, and the runtime exposes each of them as a FastAPI route
- `PlugRouter`: registers plug providers, which only contribute plug metadata to `meta.yaml` and are not exposed as FastAPI routes
- handler contexts: `BaseContext` and the context of each route family (`OrderContext`, `AgreementContext`, `ScheduleContext`, `APIContext`, and the webhook contexts); on event and webhook routes, a `ContextAdapter` declared as a router default or on the route can replace it
- pipeline primitives: `BasePipeline` and `BaseStep` compose multi-step processing over a handler context

Typical extension usage starts with creating an `ExtensionApp`, including one or more routers, and executing business logic from handlers through pipelines.

## Package Layout

The main package lives under [`mpt_extension_sdk/`](../mpt_extension_sdk).

- [`extension_app.py`](../mpt_extension_sdk/extension_app.py): public SDK entrypoint that defines `ExtensionApp`
- [`routing/`](../mpt_extension_sdk/routing): route-family routers, route definition models, and route decorators used by the SDK contract
- [`api/`](../mpt_extension_sdk/api): FastAPI payload models and builder helpers that adapt SDK routes to HTTP
- [`pipeline/`](../mpt_extension_sdk/pipeline): execution contexts, the route context factory and its context builders, decorators, pipeline base classes, and steps
- [`runtime/`](../mpt_extension_sdk/runtime): FastAPI app assembly, runtime startup, the async task runner and task transitions, logging context, and platform bootstrap helpers
- [`tasks.py`](../mpt_extension_sdk/tasks.py): `TaskHandle`, the handle a task handler uses to report to its platform task
- [`services/mpt_api_service/`](../mpt_extension_sdk/services/mpt_api_service): Marketplace service layer used by handlers, pipelines, and runtime operations
- [`services/api_client_v2/`](../mpt_extension_sdk/services/api_client_v2): lower-level async Marketplace API client (`mpt_api_client.py` extends the upstream `AsyncMPTClient` with SDK-owned endpoints under `system/`; standard resources, including integration resources, come from `mpt-api-client`). `MPTAPIService` and its sub-services are constructed with the `AsyncMPTClient` from this layer, so `api_client_v2` is a dependency of `mpt_api_service` rather than a peer
- [`settings/`](../mpt_extension_sdk/settings): runtime and extension settings discovery
- [`observability/`](../mpt_extension_sdk/observability): tracing bootstrap, instrumentation, and SDK-level observability hooks
- [`models/`](../mpt_extension_sdk/models): typed Marketplace domain models used across contexts and services, plus `TaskLog` for the log records a task handler writes to its task
- [`errors/`](../mpt_extension_sdk/errors): runtime, pipeline, and mapping exceptions
- [`webhooks/`](../mpt_extension_sdk/webhooks): the platform webhook types (`WebhookType`, `WebhookObjectType`), the typed webhook contexts, `WebhookResponse`, `WebhookError`, and the `WebhookError` subclasses the SDK answers with (`EXT001`-`EXT003`)
- [`cli/`](../mpt_extension_sdk/cli): the `mpt-ext` commands that run the extension and generate or validate `meta.yaml`

## Main Entry Points

- [`mpt_extension_sdk/extension_app.py`](../mpt_extension_sdk/extension_app.py): exposes `ExtensionApp`
- [`mpt_extension_sdk/routing/`](../mpt_extension_sdk/routing): defines route-family routers and route metadata types
- [`mpt_extension_sdk/api/builders/`](../mpt_extension_sdk/api/builders): FastAPI route builders for API, deferrable API, event, schedule, and webhook routes
- [`mpt_extension_sdk/runtime/app.py`](../mpt_extension_sdk/runtime/app.py): creates the FastAPI app, loads the exported extension app, and mounts routes
- [`mpt_extension_sdk/runtime/main.py`](../mpt_extension_sdk/runtime/main.py): exports the ASGI application instance
- [`mpt_extension_sdk/runtime/runner.py`](../mpt_extension_sdk/runtime/runner.py): runs the extension locally with `uvicorn` or on the platform with `ziticorn`
- [`mpt_extension_sdk/settings/runtime.py`](../mpt_extension_sdk/settings/runtime.py): discovers runtime configuration, metadata, and extension package entrypoints
- [`mpt_extension_sdk/settings/extension.py`](../mpt_extension_sdk/settings/extension.py): discovers `<package>.settings.ExtensionSettings`

## Runtime Model

The runtime runs locally with `FastAPI + uvicorn` and on the platform with
`mrok`/`ziticorn`; how each mode starts is described in
[sdk_usage/cli.md](sdk_usage/cli.md#running-the-extension).

A request goes through these layers:

1. `runtime/app.py` builds the FastAPI app, loads the extension's `ext_app`, and
   mounts each route through the builder of its family in `api/builders/`.
2. The route builder authenticates the request and builds the handler context
   with `RouteContextFactory` (`pipeline/factory.py`) and the family's
   `ContextBuilder` (`pipeline/builders/`).
3. API, webhook and non-task event routes run the handler inside the request.
   Schedules, task-backed events and deferred API calls are platform tasks: the
   route claims the task and submits the handler to the application-scoped
   `AsyncTaskRunner` (`runtime/async_tasks.py`), which transitions the task from
   the handler outcome (`runtime/task_transitions.py`).

How each route family behaves is described in the topic guides indexed from
[usage.md](usage.md).

## Boundaries

- Keep extension authoring primitives in `extension_app.py`, `context.py`, `tasks.py`, `routing/`, `pipeline/`, and `webhooks/`.
- Keep the FastAPI adaptation of routes under `api/`.
- Keep runtime startup, bootstrap, application assembly, task execution, and logging context under `runtime/`.
- Keep Marketplace access under `services/`: handlers and runtime modules use `mpt_api_service/` instead of raw client calls.
- Keep configuration loading under `settings/`.
- Keep tracing under `observability/`.
- Keep typed Marketplace data under `models/` and SDK exceptions under `errors/`.
- Keep the `mpt-ext` commands under `cli/`; [`pyproject.toml`](../pyproject.toml) declares the entrypoint, package metadata, and tool configuration.

## Model Status Typing

Status fields in [`models/`](../mpt_extension_sdk/models) all follow a single enum style.

**Decision: every model status is lenient. The SDK has no strict status enums.**
A status field is typed as `SomeStatus | str` (`union_mode="left_to_right"`) on the
shared base in [`models/status.py`](../mpt_extension_sdk/models/status.py)
(`CaseInsensitiveStrEnum` + `UnknownStatusWarning` + `warn_on_unknown_status`). A
known value is parsed into the enum case-insensitively; an unknown value is **kept
as a plain string and emits an `UnknownStatusWarning`** instead of failing
validation.

The rule covers both families of models that carry a status:

- **Marketplace domain models** that mirror Marketplace data (`Order`, `Agreement`,
  `Subscription`, `Asset`, `Account`, `Licensee`, `Request`).
- **Extension-framework models** that are part of the SDK's own contract with the
  platform runtime (`Extension`, `Installation`, `InstallationInvitation`, and
  `Task`).

Rationale: statuses are owned by the platform, not by the SDK, and new members can
appear at any time in either family. A status the SDK has not been taught about yet
must never break a deployed extension, so the SDK keeps the raw value and warns
instead of rejecting the payload. When adding or typing a status field, use the
lenient style; do not introduce a strict `StrEnum` status.

## Tests And Tooling

- [`tests/`](../tests) is the location for repository pytest coverage grouped by SDK domain.
- [`make/`](../make) contains canonical local commands.
- [`compose.yaml`](../compose.yaml) defines the local Docker environment used by the `make` targets.

Update this document when the package layout, main entry points, or major runtime boundaries change.
