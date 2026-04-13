# AGENTS.md

Read this repository in the following order:

1. [README.md](README.md) for the repository purpose, quick start, and documentation map.
2. [docs/architecture.md](docs/architecture.md) for the package layout and responsibilities.
3. [docs/configuration.md](docs/configuration.md) for environment variables and integration-facing settings.
4. [docs/usage.md](docs/usage.md) when a task is about how to build on top of the SDK.
5. [docs/local-development.md](docs/local-development.md) for Docker-based setup, local commands, and packaging workflows.
6. [docs/testing.md](docs/testing.md) before changing code or tests.
7. [docs/contributing.md](docs/contributing.md) for repository-specific workflow expectations.
8. [docs/migrations.md](docs/migrations.md) when a task mentions SDK compatibility changes or migration guidance.
9. [docs/documentation.md](docs/documentation.md) when changing repository documentation.

Then inspect the code paths relevant to the task:

- [`mpt_extension_sdk/core/extension.py`](mpt_extension_sdk/core/extension.py): public extension primitive that exposes the event registry and Ninja API
- [`mpt_extension_sdk/core/events/`](mpt_extension_sdk/core/events): event listener registration and event dataclasses
- [`mpt_extension_sdk/runtime/swoext.py`](mpt_extension_sdk/runtime/swoext.py): `swoext` CLI entry point and command registration
- [`mpt_extension_sdk/runtime/commands/`](mpt_extension_sdk/runtime/commands): runtime CLI subcommands
- [`mpt_extension_sdk/runtime/initializer.py`](mpt_extension_sdk/runtime/initializer.py): Django bootstrap, logging setup, and environment extraction
- [`mpt_extension_sdk/runtime/djapp/`](mpt_extension_sdk/runtime/djapp): Django application config, default settings, middleware, and management commands
- [`mpt_extension_sdk/runtime/events/`](mpt_extension_sdk/runtime/events): event dispatching, producing, and instrumentation helpers
- [`mpt_extension_sdk/mpt_http/`](mpt_extension_sdk/mpt_http): Marketplace HTTP client and request helpers
- [`mpt_extension_sdk/key_vault/`](mpt_extension_sdk/key_vault): Azure Key Vault helpers
- [`mpt_extension_sdk/airtable/`](mpt_extension_sdk/airtable): Airtable-specific HTTP error handling
- [`mpt_extension_sdk/flows/`](mpt_extension_sdk/flows): pipeline and context primitives used by extensions
- [`mpt_extension_sdk/swo_rql/`](mpt_extension_sdk/swo_rql): RQL constants and query builder utilities
- [`tests/`](tests): pytest coverage grouped by SDK domain
- [`make/`](make): canonical local commands
- [`compose.yaml`](compose.yaml): Docker-based local runtime definition
- [`pyproject.toml`](pyproject.toml): dependency, build, lint, typing, and pytest configuration

Operational guidance:

- Prefer documented `make` targets over ad hoc `uv`, Docker, or pytest invocations.
- Keep `README.md` concise and navigational. Put topic-specific details in the matching file under `docs/`.
- Keep `.github/copilot-instructions.md` thin and pointed back to this file.
- When a behavior changes, update the corresponding document in `docs/` in the same change.
- Do not invent runtime or migration guarantees that are not visible in code or tests.
