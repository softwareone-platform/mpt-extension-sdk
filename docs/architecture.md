# Architecture

This document describes repository-specific structure for the SoftwareONE Extension SDK.

## Repository Role

`mpt-extension-sdk` is a shared library repository. It provides reusable building blocks for SoftwareONE Marketplace extensions rather than a single business-specific extension service.

The repository combines:

- public SDK primitives for extension authors
- runtime bootstrapping for Django- and CLI-based execution
- integration helpers for Marketplace, Key Vault, Airtable, and telemetry concerns
- local tooling for Docker-based development, validation, and packaging

## Public SDK Concepts

The main extension authoring concepts are:

- `Extension`: combines an event registry and a Django Ninja API surface for extension endpoints
- event listeners: registered through `ext.events.listener(...)` and used for Marketplace event handling
- pipeline primitives: `Context` and `Pipeline` provide reusable multi-step processing patterns for extension logic

Typical extension usage starts with creating an `Extension` instance and then registering listeners or API routes on top of it.

## Package Layout

The main package lives under [`mpt_extension_sdk/`](../mpt_extension_sdk).

- [`core/`](../mpt_extension_sdk/core): public extension-facing primitives such as `Extension`, security helpers, and event registry types
- [`runtime/`](../mpt_extension_sdk/runtime): CLI entry points, process orchestration, Django app setup, event runtime helpers, logging, and instrumentation
- [`mpt_http/`](../mpt_extension_sdk/mpt_http): Marketplace HTTP client and related request utilities
- [`key_vault/`](../mpt_extension_sdk/key_vault): Azure Key Vault access helpers
- [`airtable/`](../mpt_extension_sdk/airtable): Airtable-specific error wrappers used by SDK consumers
- [`flows/`](../mpt_extension_sdk/flows): pipeline and context abstractions for multi-step processing
- [`swo_rql/`](../mpt_extension_sdk/swo_rql): RQL query builder helpers and constants

## Main Entry Points

- [`mpt_extension_sdk/core/extension.py`](../mpt_extension_sdk/core/extension.py): exposes the `Extension` object with an event registry and `NinjaAPI`
- [`mpt_extension_sdk/runtime/swoext.py`](../mpt_extension_sdk/runtime/swoext.py): registers the `swoext` CLI commands declared in [`pyproject.toml`](../pyproject.toml)
- [`mpt_extension_sdk/runtime/commands/run.py`](../mpt_extension_sdk/runtime/commands/run.py): runs API and consumer components through the runtime master process
- [`mpt_extension_sdk/runtime/initializer.py`](../mpt_extension_sdk/runtime/initializer.py): sets Django configuration, logging handlers, and extension environment variables before `django.setup()`
- [`mpt_extension_sdk/runtime/djapp/apps.py`](../mpt_extension_sdk/runtime/djapp/apps.py): defines the SDK Django app config and validates required webhook settings

## Runtime Model

The SDK runtime has two main surfaces:

- CLI-driven execution through `swoext`
- Django application wiring through the packaged app config entry point

The `run` command starts the runtime master process, which can run API and consumer components. Django app initialization validates required configuration such as webhook secrets for configured product ids.

## Boundaries

- Keep extension authoring primitives under `core` and `flows`.
- Keep process startup, Django concerns, and command execution under `runtime`.
- Keep external service wrappers close to the relevant integration package instead of mixing them into runtime modules.
- Keep package metadata, tool configuration, and entry points in [`pyproject.toml`](../pyproject.toml).
- Keep SDK usage guidance in [`docs/usage.md`](usage.md). Repository source documentation belongs in `README.md` and `docs/`.

## Tests And Tooling

- [`tests/`](../tests) mirrors the package layout by domain area.
- [`make/`](../make) contains canonical local commands.
- [`compose.yaml`](../compose.yaml) defines the local Docker environment used by the `make` targets.

Update this document when the package layout, main entry points, or major boundaries change.
