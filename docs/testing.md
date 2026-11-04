# Testing

This file documents repository-specific testing behavior and the shared testing
rules imported from `mpt-extension-skills`:

- [standards/unittests.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/standards/unittests.md)
- [knowledge/build-and-checks.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/build-and-checks.md)

The repository-local rules below override or narrow those shared rules where needed.

## Test Layout

`tests/` mirrors `mpt_extension_sdk/` one module at a time: the tests of
`mpt_extension_sdk/<package>/<module>.py` live in
`tests/<package>/test_<module>.py`. Do not add tests for a module to a generic or
sibling test file.

Shared fixtures live in [`tests/conftest.py`](../tests/conftest.py), and fixtures
used by one package in that package's `conftest.py`, for example the task
delivery fixtures in
[`tests/api/builders/conftest.py`](../tests/api/builders/conftest.py).

## Commands

Run the suite with `make test`, as described in the shared
[knowledge/make-targets.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/make-targets.md).
[local-development.md](local-development.md#make-commands) covers the targets
specific to this repository.

Repository-specific to testing: `make test` forwards `args` to `pytest`, so a
subset can be run without leaving the Compose runtime.

```bash
make test args="tests/cli -k meta_validate"
```

## Pytest Configuration

Repository-specific test settings come from [`pyproject.toml`](../pyproject.toml):

- tests are discovered under `tests`, with the repository root on `pythonpath`
  and `--import-mode=importlib`
- `asyncio_mode = "auto"`, so async tests need no marker
- branch coverage is collected for `mpt_extension_sdk`

## When Tests Are Required

Add or update tests when a change modifies:

- public SDK APIs
- runtime startup, registration, or CLI behavior
- HTTP or external integration helpers
- event dispatching or pipeline behavior
- observability, middleware, or settings-loading behavior

If a change only affects documentation, tests are not required.
