# Contributing

This document captures repository-specific contribution guidance.

Shared engineering rules live in `mpt-extension-skills` and should not be duplicated here:

- documentation standard: [documentation.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/standards/documentation.md)
- makefile structure: [makefiles.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/standards/makefiles.md)
- commit message rules: [commit-messages.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/standards/commit-messages.md)
- dependency management: [packages-and-dependencies.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/standards/packages-and-dependencies.md)
- pull request rules: [pull-requests.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/standards/pull-requests.md)
- Python coding conventions: [python-coding.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/standards/python-coding.md)

Shared operational knowledge also applies:

- build and validation flow: [knowledge/build-and-checks.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/build-and-checks.md)
- common make target meanings: [knowledge/make-targets.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/make-targets.md)

## Development Model

The default development model for this repository is Docker-based.

- Use `make build` to build the local image and install dependencies.
- Use `make run` to start the local runtime through Docker Compose.
- Use `make bash` when you need an interactive container session.
- Use `make build-package` when you need to produce a distributable package artifact inside the configured runtime.

## Code Organization Expectations

Repository-specific expectations:

- keep extension registration and route metadata in [`mpt_extension_sdk/extension_app.py`](../mpt_extension_sdk/extension_app.py)
- keep FastAPI route assembly under [`mpt_extension_sdk/api/`](../mpt_extension_sdk/api)
- keep reusable execution contexts, decorators, and pipelines under [`mpt_extension_sdk/pipeline/`](../mpt_extension_sdk/pipeline)
- keep runtime startup, bootstrap, logging, and app assembly under [`mpt_extension_sdk/runtime/`](../mpt_extension_sdk/runtime)
- keep Marketplace service wrappers under [`mpt_extension_sdk/services/mpt_api_service/`](../mpt_extension_sdk/services/mpt_api_service)
- keep runtime and extension configuration loading under [`mpt_extension_sdk/settings/`](../mpt_extension_sdk/settings)
- keep observability concerns under [`mpt_extension_sdk/observability/`](../mpt_extension_sdk/observability)
- keep tests under [`tests/`](../tests), mirroring production structure where practical
- update documentation in the matching file under [`docs/`](.) when there are setup, testing, migration note, or architecture changes

## Validation Before Review

Follow the shared validation flow in [knowledge/build-and-checks.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/build-and-checks.md).

Repository-specific command entry points are:

```bash
make check
make test
make check-all
```

Use `make build-package` only when you need a distributable package artifact from this repository.

See [testing.md](testing.md) for repository-specific testing expectations.

## Documentation Changes

Documentation rules live in [documentation.md](documentation.md).

When changing docs, update the smallest relevant file instead of duplicating policy across multiple documents.
