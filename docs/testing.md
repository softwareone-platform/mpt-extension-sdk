# Testing

This file documents repository-specific testing behavior and the shared testing
rules imported from `mpt-extension-skills`:

- `standards/unittests.md`
- `knowledge/build-and-checks.md`
- `knowledge/make-targets.md`

The repository-local rules below override or narrow those shared rules where
needed.

## Test Scope

The repository has pytest configured in [`pyproject.toml`](../pyproject.toml)
and the `tests/` tree already covers the main SDK domains, including:

- extension app and route registration under `tests/test_extension_app.py`
- pipeline contexts, decorators, and factories under `tests/pipeline/`
- runtime app, runner, and bootstrap behavior under `tests/runtime/`
- Marketplace service helpers under `tests/services/`
- CLI behavior under `tests/cli/`
- settings loading under `tests/settings/`
- observability bootstrap and tracing under `tests/observability/`


## Commands

Use the repository make targets:

```bash
make test
make check
make check-all
```

Repository command mapping:

- `make test` runs `pytest`
- `make check` runs local validation checks such as formatting, linting, typing, and lockfile validation
- `make check-all` runs both checks and tests

Shared make-target knowledge also applies in this repository:

- `make build`: build the local runnable or testable environment
- `make format`: automatically format the source code
- `make check`: run local validation checks
- `make test`: run the automated test suite
- `make check-all`: run the full local validation flow expected before merge
- `make bash`: open a shell in the application container or runtime environment

## Pytest Configuration

Repository-specific test settings come from [`pyproject.toml`](../pyproject.toml):

- tests are discovered under `tests`
- `pythonpath` includes the repository root
- coverage is collected for `mpt_extension_sdk`
- tests run with `--import-mode=importlib`

## Writing Tests

Repository-specific guidance:

- add or update tests next to the affected SDK domain instead of creating catch-all files
- prefer existing fixtures from [`tests/conftest.py`](../tests/conftest.py) and domain-specific `conftest.py` files
- keep external service calls mocked; do not make live Marketplace or external platform calls in tests
- cover CLI and runtime changes under `tests/cli/` or `tests/runtime/`
- cover public SDK behavior when changing `ExtensionApp`, router-family APIs, pipeline APIs, or runtime wiring


## When Tests Are Required

Add or update tests when a change modifies:

- public SDK APIs
- runtime startup, registration, or CLI behavior
- HTTP or external integration helpers
- event dispatching or pipeline behavior
- observability, middleware, or settings-loading behavior

If a change only affects documentation, tests are not required.
