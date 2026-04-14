# Local Development

This document describes repository-specific local setup and execution for the SoftwareONE Extension SDK.

## Local Execution Model

The default local workflow is Docker-based and uses [`compose.yaml`](../compose.yaml) through the repository `make` targets.

## Prerequisites

- Docker with the `docker compose` plugin
- `make`
- Python 3.12+ when you need local tooling outside Docker

## Setup

Build the local environment:

```bash
make build
```

Run the main validation commands:

```bash
make check
make test
```

## Common Commands

```bash
make build
make run
make bash
make shell
make format
make check
make test
make check-all
make build-package
```

## CLI Commands

Use the packaged `swoext` CLI inside the repository runtime when you need Django or component-level operations.

Common examples:

```bash
swoext run
swoext run api --debug --reload
swoext run consumer
swoext django <command>
swoext shell
```

## Packaging

- [`pyproject.toml`](../pyproject.toml) defines the package metadata and the `swoext` CLI entry point.
- `make build-package` runs `uv build` in the configured runtime.
- [`docs/usage.md`](usage.md) is used as the package long description.
- runtime configuration details live in [configuration.md](configuration.md)

## Local Constraints

- prefer `make` targets over ad hoc Docker commands
- prefer repository-managed dependency changes instead of editing lockfiles manually
- use the shared validation flow from [knowledge/build-and-checks.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/build-and-checks.md) before committing
