# SoftwareONE Extension SDK

`mpt-extension-sdk` is the shared Python SDK for building SoftwareONE Marketplace extensions.

The repository contains:

- core extension primitives for API and event listener registration
- runtime wiring for the `swoext` CLI, Django bootstrap, and event consumers
- shared clients and helpers for Marketplace HTTP, Key Vault, Airtable, telemetry, and RQL
- pytest coverage for the SDK modules

## Documentation

Start here:

- [AGENTS.md](AGENTS.md): entry point for AI agents
- [docs/architecture.md](docs/architecture.md): package structure and responsibilities
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
