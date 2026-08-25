# Documentation

This repository follows the shared documentation standard:

- `standards/documentation.md` in `softwareone-platform/mpt-extension-skills`

The shared standard owns the general documentation rules. This file documents
only repository-specific additions and exceptions.

## Documentation Ownership Map

This section is the authoritative map of the documentation set: it lists every
document and the topic that document owns. It is the place to look when
deciding where content belongs.

| Document | Owns |
| --- | --- |
| [`README.md`](../README.md) | human entry point: overview and quick start. Must stay short and navigational. |
| [`AGENTS.md`](../AGENTS.md) | AI entry point: the order in which an agent should read the documentation, and the code paths to inspect. Must stay operational. |
| [`architecture.md`](architecture.md) | SDK package structure, runtime model, and major boundaries. |
| [`configuration.md`](configuration.md) | SDK runtime environment variables and integration-facing settings. |
| [`usage.md`](usage.md) | SDK usage entry point and package long description. Stays navigational; full examples belong in `sdk_usage/`. |
| [`sdk_usage/`](sdk_usage/) | granular SDK consumer examples split by topic, including the `mpt-ext` command contract in [`sdk_usage/cli.md`](sdk_usage/cli.md). |
| [`local-development.md`](local-development.md) | local setup, the local stacks, and the `make` targets specific to this repository. |
| [`contributing.md`](contributing.md) | repository-specific development workflow and links to shared standards. |
| [`testing.md`](testing.md) | testing strategy, test scope, and pytest configuration. |
| [`migrations.md`](migrations.md) | SDK compatibility and migration guidance. |
| [`documentation.md`](documentation.md) | this document: the documentation rules and the ownership map above. |
| [`.github/copilot-instructions.md`](../.github/copilot-instructions.md) | thin tool adapter. Must only point back to [`AGENTS.md`](../AGENTS.md). |

[`pyproject.toml`](../pyproject.toml) uses [`usage.md`](usage.md) as the package
readme.

## Documentation Change Rule

When documentation changes, update the smallest topic-specific document, and
update the document that owns the topic according to the map above.

A topic must be described in exactly one document. Every other document links to
the owner instead of restating it. The same applies to shared standards: link to
them rather than copying their content into this repository.

[`README.md`](../README.md) and [`AGENTS.md`](../AGENTS.md) both link the
documentation set for the purposes the map gives them. Neither is an inventory,
and neither should be grown into one.
