# SoftwareONE Extension SDK

`mpt-extension-sdk` is the shared Python SDK for building SoftwareONE Marketplace extensions.

The repository contains:

- public SDK primitives centered on `ExtensionApp`, `ExtensionRouter`, and typed execution contexts
- FastAPI runtime wiring for event handlers, task-backed routes, local development (`FastAPI + uvicorn`), and platform execution (`mrok`/`ziticorn`)
- shared Marketplace service clients, settings discovery, observability hooks, and pipeline helpers
- repository tooling and documentation for building and validating the SDK itself

## Documentation

Start here:

- [AGENTS.md](AGENTS.md): entry point for AI agents
- [docs/architecture.md](docs/architecture.md): package structure, runtime model, and boundaries
- [docs/configuration.md](docs/configuration.md): runtime environment variables and integration settings
- [docs/usage.md](docs/usage.md): SDK usage guide with examples
- [docs/local-development.md](docs/local-development.md): local setup and Docker-based workflows
- [docs/testing.md](docs/testing.md): testing strategy and commands
- [docs/contributing.md](docs/contributing.md): repository-specific workflow
- [docs/migrations.md](docs/migrations.md): SDK migration notes and compatibility changes
- [docs/documentation.md](docs/documentation.md): repository documentation rules

## Quick Start

For repository work:

```bash
make build
make test
```

For SDK consumer examples and installation, see [docs/usage.md](docs/usage.md).
