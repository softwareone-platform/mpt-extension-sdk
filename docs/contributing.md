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
- Use `make bash` or `make shell` when you need an interactive container session.
- Use `make build-package` when you need to produce a distributable package artifact inside the configured runtime.

## Code Organization Expectations

Repository-specific expectations:

- keep public extension primitives close to [`mpt_extension_sdk/core/`](../mpt_extension_sdk/core)
- keep runtime bootstrapping, Django app wiring, CLI commands, and event runtime helpers under [`mpt_extension_sdk/runtime/`](../mpt_extension_sdk/runtime)
- keep external service wrappers under the matching integration package such as [`mpt_extension_sdk/mpt_http/`](../mpt_extension_sdk/mpt_http), [`mpt_extension_sdk/key_vault/`](../mpt_extension_sdk/key_vault), and [`mpt_extension_sdk/airtable/`](../mpt_extension_sdk/airtable)
- keep reusable pipeline utilities under [`mpt_extension_sdk/flows/`](../mpt_extension_sdk/flows)
- keep query-builder helpers under [`mpt_extension_sdk/swo_rql/`](../mpt_extension_sdk/swo_rql)
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
