# Local Development

This document describes repository-specific local setup and execution for the SoftwareONE Extension SDK.

## Local Execution Model

The default local workflow is Docker-based and uses [`compose.yaml`](../compose.yaml) through the repository `make` targets.

Two stacks are available. `make run` starts the extension alone, as the platform
runs it. `make run-demo` layers [`compose.demo.yaml`](../compose.demo.yaml) on
top and starts the whole local harness: the extension in `--local` mode, a second
instance used to demonstrate the claim on an execution, a WireMock devmock that
answers the Marketplace and Tasks APIs, and a Jaeger collector for traces. See
[`peripherals/devmock/README.md`](../peripherals/devmock/README.md) for the
endpoints it stubs and how to run the schedule demo.

The packaged runtime itself runs in two modes:

- local development through FastAPI + uvicorn
- platform-style execution through mrok/ziticorn after extension registration

## Prerequisites

- Docker with the `docker compose` plugin
- `make`
- Python 3.12+ when you need local tooling outside Docker

## Setup

Build the local environment before anything else:

```bash
make build
```

## Make Commands

`make help` lists every available target. The targets this repository shares
with the rest of the family — `build`, `format`, `check`, `test`, `check-all`,
`bash`, `review`, and the `uv-*` dependency targets — mean what the shared
[knowledge/make-targets.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/make-targets.md)
says they mean, and their behavior is not restated here.

The targets the shared document does not cover:

- `make run` starts the extension alone through [`compose.yaml`](../compose.yaml).
- `make run-demo` layers [`compose.demo.yaml`](../compose.demo.yaml) on top and
  starts the full local harness described in
  [Local Execution Model](#local-execution-model).
- `make down` stops and removes the Compose containers.
- `make build-package` runs `uv build` in the runtime container to produce a
  distributable package artifact.

What the shared contract leaves to each repository:

- `make check` resolves to `ruff format --check`, `ruff check`, `flake8`, `mypy`,
  and `uv lock --check` here.
- `make test` accepts pytest arguments; see [testing.md](testing.md).

`build`, `run`, `run-demo`, and `down` drive Docker Compose from the host. The
rest — `bash`, `format`, `check`, `test`, `build-package` — run their tooling
inside the Compose runtime, where the packaged `mpt-ext` CLI is available too,
for example from `make bash`. Its commands are documented in
[sdk_usage/cli.md](sdk_usage/cli.md).

## Packaging

- [`pyproject.toml`](../pyproject.toml) defines the package metadata and the `mpt-ext` CLI entry point.
- [`docs/usage.md`](usage.md) is used as the package long description.
- build the artifact with `make build-package`, described in
  [Make Commands](#make-commands).
- runtime configuration details live in [configuration.md](configuration.md)

## Local Constraints

- prefer `make` targets over ad hoc Docker commands
- prefer repository-managed dependency changes instead of editing lockfiles manually
- use the shared validation flow from [knowledge/build-and-checks.md](https://github.com/softwareone-platform/mpt-extension-skills/blob/main/knowledge/build-and-checks.md) before committing
