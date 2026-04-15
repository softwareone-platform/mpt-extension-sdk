# AGENTS.md

Working protocol for any task in this repository:

1. Identify the task type and select only the local repository files that are relevant to that task.
2. Read only those relevant local files before making changes.
3. If any selected local file references shared standards or shared operational guidance that are relevant to the same task, read those shared documents too before proceeding.
4. Treat repository-local documents as repository-specific additions, restrictions, or overrides to shared guidance.
5. If a repository-local rule conflicts with a shared rule, the local repository rule takes precedence.

When applicable, read the repository in this order:

1. [README.md](README.md) for the repository purpose, quick start, and documentation map.
2. [docs/architecture.md](docs/architecture.md) for the package layout, runtime model, and responsibilities.
3. [docs/configuration.md](docs/configuration.md) for environment variables and integration-facing settings.
4. [docs/usage.md](docs/usage.md) when a task is about how to build on top of the SDK.
5. [docs/local-development.md](docs/local-development.md) for Docker-based setup, local commands, and packaging workflows.
6. [docs/testing.md](docs/testing.md) before changing code or tests.
7. [docs/contributing.md](docs/contributing.md) for repository-specific workflow expectations.
8. [docs/migrations.md](docs/migrations.md) when a task mentions SDK compatibility changes or migration guidance.
9. [docs/documentation.md](docs/documentation.md) when changing repository documentation.

Then inspect the code paths relevant to the task:

- [`mpt_extension_sdk/extension_app.py`](mpt_extension_sdk/extension_app.py): public SDK entrypoint that defines `ExtensionApp`, `ExtensionRouter`, route registration, and context adaptation
- [`mpt_extension_sdk/api/router.py`](mpt_extension_sdk/api/router.py): FastAPI route builders for task and non-task handlers, event execution, and task lifecycle wiring
- [`mpt_extension_sdk/pipeline/`](mpt_extension_sdk/pipeline): execution contexts, pipeline primitives, step decorators, and context factory helpers
- [`mpt_extension_sdk/runtime/app.py`](mpt_extension_sdk/runtime/app.py): FastAPI app assembly, middleware registration, observability bootstrap, and extension route mounting
- [`mpt_extension_sdk/runtime/main.py`](mpt_extension_sdk/runtime/main.py): exported ASGI application used by local and platform runtimes
- [`mpt_extension_sdk/runtime/runner.py`](mpt_extension_sdk/runtime/runner.py): local `uvicorn` startup, platform `ziticorn` startup, and metadata generation before launch
- [`mpt_extension_sdk/runtime/bootstrap/`](mpt_extension_sdk/runtime/bootstrap): extension instance registration, platform identity persistence, and bootstrap HTTP calls
- [`mpt_extension_sdk/services/mpt_api_service/`](mpt_extension_sdk/services/mpt_api_service): Marketplace service layer used by handlers, pipelines, and runtime task operations
- [`mpt_extension_sdk/settings/`](mpt_extension_sdk/settings): runtime and extension settings discovery from environment variables and extension modules
- [`mpt_extension_sdk/observability/`](mpt_extension_sdk/observability): tracing, logging, and FastAPI instrumentation hooks
- [`mpt_extension_sdk/models/`](mpt_extension_sdk/models): shared typed Marketplace domain models used by contexts and services
- [`tests/`](tests): pytest coverage grouped by SDK domain
- [`make/`](make): canonical local commands
- [`compose.yaml`](compose.yaml): Docker-based local runtime definition
- [`pyproject.toml`](pyproject.toml): dependency, build, lint, typing, and pytest configuration

Operational guidance:

- Prefer documented `make` targets over ad hoc `uv`, Docker, or pytest invocations.
- Keep `README.md` concise and navigational. Put topic-specific details in the matching file under `docs/`.
- Keep `.github/copilot-instructions.md` thin and pointed back to this file.
- When a behavior changes, update the corresponding document in `docs/` in the same change.
- Describe the runtime as `FastAPI + uvicorn` for local development and `mrok`/`ziticorn` for platform execution unless the code changes.
- Do not invent runtime, migration, or testing guarantees that are not visible in code or tests.
