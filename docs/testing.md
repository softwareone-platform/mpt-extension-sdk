# Testing

This file documents repository-specific testing behavior and the shared testing
rules imported from `mpt-extension-skills`:

- `standards/unittests.md`
- `knowledge/build-and-checks.md`
- `knowledge/make-targets.md`

The repository-local rules below override or narrow those shared rules where
needed.

## Test Scope

The repository currently has pytest configured in [`pyproject.toml`](../pyproject.toml),
but the `tests/` tree is not yet populated with stable domain coverage.

When adding coverage, organize tests by SDK domain, for example:

- extension app and route registration under `tests/extension_app/` or equivalent
- pipeline contexts, decorators, and factories under `tests/pipeline/`
- runtime app, runner, and bootstrap behavior under `tests/runtime/`
- Marketplace service helpers under `tests/services/`
- CLI behavior under `tests/cli/`

Shared unit-test scope also applies:

- use `pytest` for unit tests
- write tests as functions, not classes
- do not add type annotations to test functions
- keep test files and test functions under the `test_` naming convention
- do not add test docstrings
- keep the `tests/` layout aligned with the source layout

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
- `make shell`: open an application-specific shell

## Pytest Configuration

Repository-specific test settings come from [`pyproject.toml`](../pyproject.toml):

- tests are discovered under `tests`
- `pythonpath` includes the repository root
- coverage is collected for `mpt_extension_sdk`
- tests run with `--import-mode=importlib`

## Writing Tests

Repository-specific guidance:

- add or update tests next to the affected SDK domain instead of creating catch-all files
- keep external service calls mocked; do not make live Marketplace or external platform calls in tests
- cover public SDK behavior when changing `ExtensionApp`, `ExtensionRouter`, pipeline APIs, or runtime wiring
- cover CLI and runtime changes under `tests/cli/` or `tests/runtime/`
- prefer smoke and regression tests for imports, route registration, context building, and startup flows before broadening coverage

Shared unit-test rules that must be followed in this repository:

- follow AAA (Arrange, Act, Assert); keep the act step explicit and easy to spot
- do not put branching logic inside tests; use `@pytest.mark.parametrize` for permutations
- prefer a single logical assertion per test; if several assertions validate one result object, keep them tightly related
- test branches as close as possible to the function where the branch exists

## When Tests Are Required

Add or update tests when a change modifies:

- public SDK APIs
- runtime startup, registration, or CLI behavior
- HTTP or external integration helpers
- event dispatching or pipeline behavior
- observability, middleware, or settings-loading behavior

If a change only affects documentation, tests are not required.

## Validation Flow

The shared build-and-checks workflow applies here with repository-specific
targets:

1. Run `make build` if `uv.lock` changed.
2. Then run `make check-all`.

These commands are expected to run sequentially in that order.

Before committing:

- make sure `pre-commit` is installed or updated locally
- review the automatic `pre-commit` output during `git commit`
- treat the commit as incomplete until the hooks pass cleanly
