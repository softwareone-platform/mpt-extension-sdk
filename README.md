[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=softwareone-platform_mpt-extension-sdk&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=softwareone-platform_mpt-extension-sdk)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=softwareone-platform_mpt-extension-sdk&metric=coverage)](https://sonarcloud.io/summary/new_code?id=softwareone-platform_mpt-extension-sdk)

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

# SoftwareONE Extension SDK

SDK for SoftwareONE python extensions

## Getting started

### Prerequisites

- Docker and Docker Compose plugin (`docker compose` CLI)
- `make`
- Valid `.env` file
- Adobe credentials and authorizations JSON files in the project root
- [CodeRabbit CLI](https://www.coderabbit.ai/cli) (optional. Used for running review check locally)


### Make targets overview

Common development workflows are wrapped in the `makefile`:

- `make help` – list available commands
- `make bash` – start the app container and open a bash shell
- `make build` – build the application image for development
- `make build-package` – build the package locally
- `make check` – run code quality checks (ruff, flake8, lockfile check)
- `make check-all` – run checks, formatting, and tests
- `make down` – stop and remove containers
- `make format` – apply formatting and import fixes
- `make review` –  check the code in the cli by running CodeRabbit
- `make shell` – open a Django shell inside the running app container
- `make test` – run the test suite with pytest

## Running tests

Tests run inside Docker using the dev configuration.

Run the full test suite:

```bash
make test
```

Pass additional arguments to pytest using the `args` variable:

```bash
make test args="-k test_bla -vv"
make test args="tests/test_bla.py"
```

## Developer utilities

Useful helper targets during development:

```bash
make bash          # open a bash shell in the app container
make build-package # build the package locally
make check         # run ruff, flake8, and lockfile checks
make check-all     # run checks and tests
make format        # auto-format code and imports
make review        # check the code in the cli by running CodeRabbit
```
