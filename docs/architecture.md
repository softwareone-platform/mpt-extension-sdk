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

- `ExtensionApp`: the root SDK object for one extension package; it owns route registration, metadata generation, and optional context adaptation
- route-family routers: `EventRouter`, `APIRouter`, `ScheduleRouter`, `PlugRouter`, and `WebhookRouter` group related handlers under a shared prefix before they are included in the extension app
- event handlers: task and non-task callbacks registered on `EventRouter` and exposed as FastAPI routes by the runtime
- pipeline primitives: `ExecutionContext`, specialized order/agreement contexts, `BasePipeline`, and `BaseStep` provide reusable multi-step processing patterns

Typical extension usage starts with creating an `ExtensionApp`, registering one or more routers, and executing business logic from handlers through pipelines.

## Package Layout

The main package lives under [`mpt_extension_sdk/`](../mpt_extension_sdk).

- [`extension_app.py`](../mpt_extension_sdk/extension_app.py): public SDK entrypoint that defines `ExtensionApp`
- [`routing/`](../mpt_extension_sdk/routing): route-family routers, route definition models, and route decorators used by the SDK contract
- [`api/`](../mpt_extension_sdk/api): FastAPI payload models and builder helpers that adapt SDK routes to HTTP
- [`pipeline/`](../mpt_extension_sdk/pipeline): execution contexts, the route context factory and its context builders, decorators, pipeline base classes, and steps
- [`runtime/`](../mpt_extension_sdk/runtime): FastAPI app assembly, runtime startup, logging context, and platform bootstrap helpers
- [`tasks.py`](../mpt_extension_sdk/tasks.py): `TaskHandle`, which gives task-backed handlers such as schedules the platform task id, best-effort task logging and progress reporting, and task parameter updates, without exposing the task lifecycle
- [`services/mpt_api_service/`](../mpt_extension_sdk/services/mpt_api_service): Marketplace service layer used by handlers, pipelines, and runtime operations
- [`services/api_client_v2/`](../mpt_extension_sdk/services/api_client_v2): lower-level async Marketplace API client (`mpt_api_client.py` extends the upstream `AsyncMPTClient` with SDK-owned endpoints under `system/`; standard resources, including integration resources, come from `mpt-api-client`). `MPTAPIService` and its sub-services are constructed with the `AsyncMPTClient` from this layer, so `api_client_v2` is a dependency of `mpt_api_service` rather than a peer
- [`settings/`](../mpt_extension_sdk/settings): runtime and extension settings discovery
- [`observability/`](../mpt_extension_sdk/observability): tracing bootstrap, instrumentation, and SDK-level observability hooks
- [`models/`](../mpt_extension_sdk/models): typed Marketplace domain models used across contexts and services, plus `TaskLog` for the log records a task handler writes to its task
- [`errors/`](../mpt_extension_sdk/errors): runtime, pipeline, and mapping exceptions
- [`webhooks/`](../mpt_extension_sdk/webhooks): the platform webhook types (`WebhookType`) and the object type each one carries (`WebhookObjectType`)

## Main Entry Points

- [`mpt_extension_sdk/extension_app.py`](../mpt_extension_sdk/extension_app.py): exposes `ExtensionApp`
- [`mpt_extension_sdk/routing/`](../mpt_extension_sdk/routing): defines route-family routers and route metadata types
- [`mpt_extension_sdk/api/builders/`](../mpt_extension_sdk/api/builders): FastAPI route builders for API, deferrable API, event, and schedule routes
- [`mpt_extension_sdk/runtime/app.py`](../mpt_extension_sdk/runtime/app.py): creates the FastAPI app, loads the exported extension app, and mounts routes
- [`mpt_extension_sdk/runtime/main.py`](../mpt_extension_sdk/runtime/main.py): exports the ASGI application instance
- [`mpt_extension_sdk/runtime/runner.py`](../mpt_extension_sdk/runtime/runner.py): runs the extension locally with `uvicorn` or on the platform with `ziticorn`
- [`mpt_extension_sdk/settings/runtime.py`](../mpt_extension_sdk/settings/runtime.py): discovers runtime configuration, metadata, and extension package entrypoints
- [`mpt_extension_sdk/settings/extension.py`](../mpt_extension_sdk/settings/extension.py): discovers `<package>.settings.ExtensionSettings`

## Runtime Model

### Run modes

The SDK runtime has two main execution surfaces:

- local development through `FastAPI + uvicorn`
- platform execution through `mrok`/`ziticorn`, after extension registration and identity bootstrap

`runtime/main.py` writes `meta.yaml` while the ASGI application is imported, so it happens in both run modes,
using the metadata-file writer from `runtime/runner.py`. In platform mode `runtime/runner.py` registers the
extension instance, persists the returned identity when present, and starts the exported ASGI app through Ziticorn.
Registration runs in the runner process before Ziticorn starts the workers, so the runner hands the registered
instance id to the workers through the environment (see [configuration.md](configuration.md)).
Ziticorn serves `/bypass/*` over plain HTTP instead of over the OpenZiti overlay, so platform probes reach the
operational endpoints.

### Application assembly

`runtime/app.py` assembles the FastAPI app, configures middleware and observability,
loads the extension's exported `ext_app`, and mounts every registered route through
the builder of its family in `api/builders/`. It also registers the operational
endpoints under `/bypass` (see
[sdk_usage/application.md](sdk_usage/application.md#operational-endpoints)).
Its lifespan runs the startup hooks registered through `ExtensionApp.on_startup`
before the app reports itself as ready, so serve-time initialization stays out of
`app.py` import time and never runs during metadata generation.

### Context building and request execution

Every route family builds its handler context through `RouteContextFactory`
(`pipeline/factory.py`). The factory checks that the token targets this extension,
creates the account-scoped and vendor-scoped Marketplace services, and hands them,
with the settings, to the `ContextBuilder` of the family in `pipeline/builders/`
(`APIContextBuilder`, `EventContextBuilder`, `ScheduleContextBuilder`). Each route
builder creates one factory when the route is mounted and passes it to the code
that answers the request; the factory reads the process settings on each build, so
mounting routes does not need them.

Synchronous HTTP routes share `RouteRequestExecutor`
(`api/builders/request_executor.py`). It authenticates the request, builds the
context, runs the handler inside the route span, and answers authentication and
unexpected errors with the family's `RouteErrorResponseBuilder`
(`api/builders/errors.py`). `APIRequestExecutor` implements it for API routes.
`resolve_handler_result` (`api/builders/handlers.py`) lets event and API handlers
be sync or async.

### Route families

The `event`, `api`, and `schedule` route families are implemented end-to-end in
runtime request handling. The `plug` route family is implemented as declarative
metadata with static asset exposure under `/static`. The `webhook` route family is
only published in metadata for now; the runtime refuses to mount it. What each
family publishes in `meta.yaml` is described in [sdk_usage/cli.md](sdk_usage/cli.md#metadata-metayaml).

Each route family documents its own contract:

- events: [sdk_usage/events.md](sdk_usage/events.md)
- schedules: [sdk_usage/schedules.md](sdk_usage/schedules.md)
- API routes, deferrable endpoints included: [sdk_usage/api.md](sdk_usage/api.md)
- webhooks: [sdk_usage/webhooks.md](sdk_usage/webhooks.md)
- plugs: [sdk_usage/plugs.md](sdk_usage/plugs.md)

Error mapping for all of them is described in
[sdk_usage/error-handling.md](sdk_usage/error-handling.md).

### Task execution

Schedule handlers are executed asynchronously by an application-scoped runner,
so durable dispatch and the claim on an execution stay with the Extension
Framework and the platform task rather than with the SDK. The same runner executes
deferred API calls: a deferrable API route serves both modes on one path. A request
without the `MPT-Task-Id` header runs as a direct call; a request with it is a
deferred delivery of that platform task, answered with an event response. A route
restricted to deferred delivery answers a direct call with `405 Method Not Allowed`. The
declaration and its registration rules are described in
[sdk_usage/api.md](sdk_usage/api.md#deferrable-endpoints).

Every task the SDK claims, whatever route family delivered it, records the
instance that ran it: after a successful claim, `runtime/task_transitions.py`
writes the instance id to the task's `instanceId` parameter. Recording it is best-effort: a failure is logged as a
warning and the claim still counts.

## Boundaries

- Keep extension authoring primitives in `extension_app.py`, `routing/`, and `pipeline/`.
- Keep FastAPI adapter/builders under `api/`.
- Keep runtime startup, bootstrap, and application assembly under `runtime/`.
- Keep Marketplace access logic under `services/mpt_api_service/` instead of duplicating raw client usage in handlers or runtime modules.
- Keep configuration loading under `settings/`.
- Keep tracing and logging concerns under `observability/`.
- Keep package metadata, tool configuration, and CLI entrypoints in [`pyproject.toml`](../pyproject.toml).
- Keep SDK usage guidance indexed from [`docs/usage.md`](usage.md), with granular
  examples under [`docs/sdk_usage/`](sdk_usage/). Repository source documentation
  belongs in `README.md` and `docs/`.

## Model Status Typing

Status fields in [`models/`](../mpt_extension_sdk/models) all follow a single enum
style.

**Decision: every model status is lenient. The SDK has no strict status enums.**
A status field is typed as `SomeStatus | str` (`union_mode="left_to_right"`) on the
shared base in [`models/status.py`](../mpt_extension_sdk/models/status.py)
(`CaseInsensitiveStrEnum` + `UnknownStatusWarning` + `warn_on_unknown_status`). A
known value is parsed into the enum case-insensitively; an unknown value is **kept
as a plain string and emits an `UnknownStatusWarning`** instead of failing
validation.

The rule covers both families of models that carry a status:

- **Marketplace domain models** that mirror Marketplace data (`Order`, `Agreement`,
  `Subscription`, `Asset`, `Account`, `Licensee`).
- **Extension-framework models** that are part of the SDK's own contract with the
  platform runtime (`Extension`, `Installation`, `InstallationInvitation`, and
  `Task` for schedule execution).

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
