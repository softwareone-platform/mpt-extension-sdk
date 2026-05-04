# Testing

Shared unit-test rules live in [unittests.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/standards/unittests.md).

Shared build and target knowledge also applies:

- [knowledge/build-and-checks.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/build-and-checks.md)
- [knowledge/make-targets.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/make-targets.md)

This file documents repository-specific testing behavior.

## Test Scope

The repository currently has stable coverage in these areas:

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
- `make check` runs `ruff format --check`, `ruff check`, `flake8`, `mypy` and `uv lock --check`
- `make check-all` runs both checks and tests

The CI workflow in [`.github/workflows/pr-build-merge.yml`](../.github/workflows/pr-build-merge.yml) uses the same `make build` and `make check-all` flow.

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
