# SoftwareONE Extension SDK

`mpt-extension-sdk` is the shared Python SDK for building SoftwareONE Marketplace extensions.

The repository contains:

- public SDK primitives centered on `ExtensionApp`, `ExtensionRouter`, and typed execution contexts
- FastAPI runtime wiring for event handlers, task-backed routes, local development (`FastAPI + uvicorn`), and platform execution (`mrok`/`ziticorn`)
- shared Marketplace service clients, settings discovery, observability hooks, and pipeline helpers
- a Typer-based `mpt-ext` CLI for runtime startup and metadata generation/validation
- repository tooling and documentation for building and validating the SDK itself

## Documentation

Shortcuts to the documents a reader is most likely to want next. This is not the
full inventory: [docs/documentation.md](docs/documentation.md) holds the
authoritative map of every document and the topic it owns.

- [docs/usage.md](docs/usage.md): SDK usage guide with examples
- [docs/architecture.md](docs/architecture.md): package structure, runtime model, and boundaries
- [docs/configuration.md](docs/configuration.md): runtime environment variables and integration settings
- [docs/local-development.md](docs/local-development.md): local setup, Docker-based workflows, and repository-specific `make` targets
- [docs/contributing.md](docs/contributing.md): repository-specific workflow
- [AGENTS.md](AGENTS.md): entry point for AI agents

## Quick Start

For repository work:

```bash
make build
make test
```

For the local stacks and this repository's `make` targets, see
[docs/local-development.md](docs/local-development.md). For SDK consumer
examples and installation, see [docs/usage.md](docs/usage.md).
