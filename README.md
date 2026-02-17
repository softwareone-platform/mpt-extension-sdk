[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=softwareone-platform_mpt-extension-sdk&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=softwareone-platform_mpt-extension-sdk)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=softwareone-platform_mpt-extension-sdk&metric=coverage)](https://sonarcloud.io/summary/new_code?id=softwareone-platform_mpt-extension-sdk)

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

# SoftwareONE Extension SDK

SDK for SoftwareONE python extensions

## Getting started

### Prerequisites

- Docker and Docker Compose plugin (`docker compose` CLI)
- `make`
- [CodeRabbit CLI](https://www.coderabbit.ai/cli) (optional. Used for running review check locally)


### Make targets overview

Common development workflows are wrapped in the `Makefile`. Run `make help` to see the list of available commands.

### How the Makefile works

The project uses a modular Makefile structure that organizes commands into logical groups:

- **Main Makefile** (`Makefile`): Entry point that automatically includes all `.mk` files from the `make/` directory
- **Modular includes** (`make/*.mk`): Commands are organized by category:
  - `common.mk` - Core development commands (build, test, format, etc.)
  - `repo.mk` - Repository management and dependency commands
  - `migrations.mk` - Database migration commands (Only available in extension repositories)
  - `external_tools.mk` - Integration with external tools


You can extend the Makefile with your own custom commands creating a `local.mk` file inside make folder. This file is
automatically ignored by git, so your personal commands won't affect other developers or appear in version control.


### Setup

Follow these steps to set up the development environment:

#### 1. Clone the repository

```bash
git clone <repository-url>
```
```bash
cd mpt-extension-sdk
```

#### 2. Build the Docker images

Build the development environment:

```bash
make build
```

This will create the Docker images with all required dependencies and the virtualenv.

#### 3. Verify the setup

Run the test suite to ensure everything is configured correctly:

```bash
make test
```


## Developer utilities

Useful helper targets during development:

```bash
make bash          # open a bash shell in the app container
make check         # run ruff, flake8, and lockfile checks
make check-all     # run checks and tests
make format        # auto-format code and imports
make review        # check the code in the cli by running CodeRabbit
```

## Migration Guide

### API Version Change (February 2026)

The MPT Extension SDK now uses the standardized API path `/public/v1/` instead of `/v1/`.

#### What Changed

- **MPTClient** now automatically appends `/public/v1/` to the base URL
- The `MPT_API_BASE_URL` environment variable should **not** include any version path

#### Migration Steps

**Before:**
```bash
# Old configuration (deprecated)
export MPT_API_BASE_URL=https://api.example.com/v1
```

**After:**
```bash
# New configuration (recommended)
export MPT_API_BASE_URL=https://api.example.com
```

#### Backward Compatibility

The SDK maintains backward compatibility with old configurations:
- URLs with `/v1/` or `/v1` will trigger a deprecation warning but continue to work
- URLs with `/public/v1` are also supported
- All formats will produce the correct final URL: `https://api.example.com/public/v1/`

#### Example

```python
from mpt_extension_sdk.mpt_http.base import MPTClient

# Recommended usage
client = MPTClient(base_url="https://api.example.com", api_token="your-token")
# Results in: https://api.example.com/public/v1/

# Old format (will show deprecation warning)
client = MPTClient(base_url="https://api.example.com/v1/", api_token="your-token")
# Still works, results in: https://api.example.com/public/v1/
```

**Action Required:** Update your `MPT_API_BASE_URL` configuration to remove any version path suffixes.
