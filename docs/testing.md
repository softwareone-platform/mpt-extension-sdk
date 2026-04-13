# Testing

Shared unit-test rules live in [unittests.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/standards/unittests.md).

Shared build and target knowledge also applies:

- [knowledge/build-and-checks.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/build-and-checks.md)
- [knowledge/make-targets.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/make-targets.md)

This file documents repository-specific testing behavior.

## Test Scope

The repository currently has stable coverage in these areas:

- core extension primitives and security helpers under [`tests/core/`](../tests/core)
- event registry behavior under [`tests/core/events/`](../tests/core/events)
- pipeline and context utilities under [`tests/flows/`](../tests/flows)
- Marketplace HTTP helpers under [`tests/mpt_http/`](../tests/mpt_http)
- Key Vault wrappers under [`tests/key_vault/`](../tests/key_vault)
- Airtable error handling under [`tests/airtable/`](../tests/airtable)
- runtime CLI, initialization, Django app wiring, commands, workers, and event runtime behavior under [`tests/runtime/`](../tests/runtime)
- RQL query builder helpers under [`tests/swo_rql/`](../tests/swo_rql)

## Commands

Use the repository make targets:

```bash
make test
make check
make check-all
```

Repository command mapping:

- `make test` runs `pytest`
- `make check` runs `ruff format --check`, `ruff check`, `flake8`, and `uv lock --check`
- `make check-all` runs both checks and tests

## Pytest Configuration

Repository-specific test settings come from [`pyproject.toml`](../pyproject.toml):

- tests are discovered under `tests`
- `pythonpath` includes the repository root
- coverage is collected for `mpt_extension_sdk`
- tests run with `--import-mode=importlib`
- Django-backed tests use `tests.django.settings`

## Writing Tests

Repository-specific guidance:

- add or update tests next to the affected SDK domain instead of creating catch-all files
- prefer existing fixtures from [`tests/conftest.py`](../tests/conftest.py) and domain-specific `conftest.py` files
- keep external service calls mocked; do not make live Marketplace, Azure, or Airtable calls in tests
- cover CLI and runtime changes under [`tests/runtime/`](../tests/runtime)
- cover public extension behavior under [`tests/core/`](../tests/core) when changing developer-facing APIs

## When Tests Are Required

Add or update tests when a change modifies:

- public SDK APIs
- runtime initialization or CLI behavior
- HTTP or external integration helpers
- event dispatching or pipeline behavior
- security, middleware, or Django app configuration behavior

If a change only affects documentation, tests are not required.
