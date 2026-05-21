# Documentation

This repository follows the shared documentation standard:

- `standards/documentation.md` in `softwareone-platform/mpt-extension-skills`

The shared standard owns the general documentation rules. This file documents
only repository-specific additions and exceptions.

## Repository Rules

- `README.md` must stay short and act as the main human entry point.
- `AGENTS.md` must stay operational and tell AI agents which files to read first.
- `docs/architecture.md` must describe the SDK package structure and boundaries.
- `docs/configuration.md` must hold SDK runtime environment-variable guidance.
- `docs/usage.md` must stay as the SDK usage entry point and package long
  description.
- `docs/sdk_usage/` must hold granular SDK consumer examples split by topic.
- topic-specific behavior must live in the matching file under [`docs/`](.).
- `.github/copilot-instructions.md` must remain a thin adapter that points back
  to [`AGENTS.md`](../AGENTS.md).
- `pyproject.toml` uses [`docs/usage.md`](usage.md) as the package readme.

## Current Documentation Map

- [`README.md`](../README.md): human entry point, overview, quick start, and documentation map
- [`AGENTS.md`](../AGENTS.md): AI entry point and reading order
- [`architecture.md`](architecture.md): package structure and major boundaries
- [`configuration.md`](configuration.md): runtime variables and integration-facing settings
- [`usage.md`](usage.md): SDK usage entry point and package long description
- [`sdk_usage/`](sdk_usage/): granular SDK usage examples split by topic
- [`local-development.md`](local-development.md): local setup and command entry points
- [`contributing.md`](contributing.md): repository-specific development workflow
- [`testing.md`](testing.md): testing strategy and command mapping
- [`migrations.md`](migrations.md): SDK compatibility guidance

## Documentation Change Rule

When documentation changes, update the smallest topic-specific document. Keep
[`docs/usage.md`](usage.md) navigational and put full examples in
[`docs/sdk_usage/`](sdk_usage/).
