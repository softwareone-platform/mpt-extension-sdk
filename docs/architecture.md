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
- route-family routers: `EventRouter`, `ApiRouter`, `ScheduleRouter`, and `PlugRouter` group related handlers under a shared prefix before they are included in the extension app
- event handlers: task and non-task callbacks registered on `EventRouter` and exposed as FastAPI routes by the runtime
- pipeline primitives: `ExecutionContext`, specialized order/agreement contexts, `BasePipeline`, and `BaseStep` provide reusable multi-step processing patterns

Typical extension usage starts with creating an `ExtensionApp`, registering one or more routers, and executing business logic from handlers through pipelines.

## Package Layout

The main package lives under [`mpt_extension_sdk/`](../mpt_extension_sdk).

- [`extension_app.py`](../mpt_extension_sdk/extension_app.py): public SDK entrypoint that defines `ExtensionApp`
- [`routing/`](../mpt_extension_sdk/routing): route-family routers and route definition models used by the SDK contract
- [`api/`](../mpt_extension_sdk/api): FastAPI payload models and builder helpers that adapt SDK routes to HTTP
- [`pipeline/`](../mpt_extension_sdk/pipeline): execution contexts, context factory helpers, decorators, pipeline base classes, and steps
- [`runtime/`](../mpt_extension_sdk/runtime): FastAPI app assembly, runtime startup, logging context, and platform bootstrap helpers
- [`services/mpt_api_service/`](../mpt_extension_sdk/services/mpt_api_service): Marketplace service layer used by handlers, pipelines, and runtime operations
- [`settings/`](../mpt_extension_sdk/settings): runtime and extension settings discovery
- [`observability/`](../mpt_extension_sdk/observability): tracing bootstrap, instrumentation, and SDK-level observability hooks
- [`models/`](../mpt_extension_sdk/models): typed Marketplace domain models used across contexts and services
- [`errors/`](../mpt_extension_sdk/errors): runtime, pipeline, and mapping exceptions

## Main Entry Points

- [`mpt_extension_sdk/extension_app.py`](../mpt_extension_sdk/extension_app.py): exposes `ExtensionApp`
- [`mpt_extension_sdk/routing/`](../mpt_extension_sdk/routing): defines route-family routers and route metadata types
- [`mpt_extension_sdk/api/router.py`](../mpt_extension_sdk/api/router.py): façade for FastAPI route builders
- [`mpt_extension_sdk/runtime/app.py`](../mpt_extension_sdk/runtime/app.py): creates the FastAPI app, loads the exported extension app, and mounts routes
- [`mpt_extension_sdk/runtime/main.py`](../mpt_extension_sdk/runtime/main.py): exports the ASGI application instance
- [`mpt_extension_sdk/runtime/runner.py`](../mpt_extension_sdk/runtime/runner.py): runs the extension locally with `uvicorn` or on the platform with `ziticorn`
- [`mpt_extension_sdk/settings/runtime.py`](../mpt_extension_sdk/settings/runtime.py): discovers runtime configuration, metadata, and extension package entrypoints
- [`mpt_extension_sdk/settings/extension.py`](../mpt_extension_sdk/settings/extension.py): discovers `<package>.settings.ExtensionSettings`

## Runtime Model

The SDK runtime has two main execution surfaces:

- local development through `FastAPI + uvicorn`
- platform execution through `mrok`/`ziticorn`, after extension registration and identity bootstrap

`runtime/runner.py` generates `meta.yaml` before startup. In platform mode it registers the extension instance, persists the returned identity when present, and starts the exported ASGI app through Ziticorn. `runtime/app.py` assembles the FastAPI app, configures middleware and observability, loads the extension's exported `ext_app`, and mounts every registered route.

At the moment, only the `event` route family is implemented end-to-end in runtime and metadata generation. `api`, `schedule`, and `plug` route families are modeled in the SDK contract but are not yet mounted by the runtime or emitted into `meta.yaml`.

## Boundaries

- Keep extension authoring primitives in `extension_app.py`, `routing/`, and `pipeline/`.
- Keep FastAPI adapter/builders under `api/`.
- Keep runtime startup, bootstrap, and application assembly under `runtime/`.
- Keep Marketplace access logic under `services/mpt_api_service/` instead of duplicating raw client usage in handlers or runtime modules.
- Keep configuration loading under `settings/`.
- Keep tracing and logging concerns under `observability/`.
- Keep package metadata, tool configuration, and CLI entrypoints in [`pyproject.toml`](../pyproject.toml).
- Keep SDK usage guidance in [`docs/usage.md`](usage.md). Repository source documentation belongs in `README.md` and `docs/`.

## Tests And Tooling

- [`tests/`](../tests) is the location for repository pytest coverage grouped by SDK domain.
- [`make/`](../make) contains canonical local commands.
- [`compose.yaml`](../compose.yaml) defines the local Docker environment used by the `make` targets.

Update this document when the package layout, main entry points, or major runtime boundaries change.
