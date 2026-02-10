# MPT Extension SDK

The **MPT Extension SDK** is an SDK for building extensions on the SoftwareONE Marketplace Platform (MPT).

## Quick Start

1. **Install the SDK:**
    ```bash
    pip install mpt-extension-sdk
    ```

2. **Create your extension:**
    ```python
    from mpt_extension_sdk.core.extension import Extension

    ext = Extension()

    @ext.events.listener("orders")
    def process_order(client, event):
        """Process order"""
        # Process your order logic here
    ```

3. **Run the extension:**
    ```bash
    make run
    ```

## Installation

Install with pip or your favorite PyPI package manager:

```bash
pip install mpt-extension-sdk
```

```bash
uv add mpt-extension-sdk
```

## Prerequisites

- Python 3.12+
- Docker and Docker Compose (for development)
- Access to SoftwareONE Marketplace Platform API
- Environment variables configured (see [Environment Variables](#environment-variables))

## Environment Variables

The SDK uses the following environment variables:

| Variable                                | Default                  | Example                                 | Description                                                                               |
|-----------------------------------------|--------------------------|-----------------------------------------|-------------------------------------------------------------------------------------------|
| `EXT_WEBHOOKS_SECRETS`                  | -                        | {"PRD-1111-1111": "123qweasd3432234"}   | Webhook secret of the Draft validation Webhook in SoftwareONE Marketplace for the product |
| `MPT_API_BASE_URL`                      | `http://localhost:8000`  | `https://portal.softwareone.com/mpt`    | SoftwareONE Marketplace API URL                                                           |
| `MPT_API_TOKEN`                         | -                        | eyJhbGciOiJSUzI1N...                    | SoftwareONE Marketplace API Token                                                         |
| `MPT_PRODUCTS_IDS`                      | PRD-1111-1111            | PRD-1234-1234,PRD-4321-4321             | Comma-separated list of SoftwareONE Marketplace Product ID                                |
| `MPT_PORTAL_BASE_URL`                   | `http://localhost:8000`  | `https://portal.softwareone.com`        | SoftwareONE Marketplace Portal URL                                                        |
| `MPT_ORDERS_API_POLLING_INTERVAL_SECS`  | 120                      | 60                                      | Orders polling interval from the Software Marketplace API in seconds                      |


**Example `.env` file:**

```dotenv
EXT_WEBHOOKS_SECRETS={"PRD-1111-1111":"<webhook-secret-for-product>","PRD-2222-2222":"<webhook-secret-for-product>"}
MPT_API_BASE_URL=https://api.s1.show/public
MPT_API_TOKEN=<your-api-token>
MPT_PRODUCTS_IDS=PRD-1111-1111,PRD-2222-2222
MPT_PORTAL_BASE_URL=https://portal.s1.show
```

## Core Components

### Extension

The `Extension` class is the foundation of your MPT extension. It provides:

- **Event Registry**: Register event listeners for MPT platform events
- **API Integration**: Built-in Django Ninja API for REST endpoints

```python
import logging
from http import HTTPStatus

from django.conf import settings
from mpt_extension_sdk.core.extension import Extension
from mpt_extension_sdk.core.security import JWTAuth
from mpt_extension_sdk.mpt_http.mpt import get_webhook
from mpt_extension_sdk.runtime.djapp.conf import get_for_product

logger = logging.getLogger(__name__)

ext = Extension()

@ext.events.listener("orders")
def process_order(client, event) -> None:
    """Process order events from MPT."""
    logger.info(f"Processing {event.type}")
    # Your logic here

def jwt_secret_callback(client, claims):
    """Retrieve webhook secret for JWT validation."""
    return "your-webhook-secret"

@ext.api.post(
  "/v1/orders/validate",
  auth=JWTAuth(jwt_secret_callback),
)
def process_order_validation(request , order):
    """Start order process validation."""
    # Your logic here
```


### Pipeline Processing

The SDK includes a pipeline system for building complex processing workflows:

```python
from mpt_extension_sdk.flows.context import Context
from mpt_extension_sdk.flows.pipeline import Pipeline

class ValidateOrderStep:
    def process(self, client, context) -> None:
        """Validation Order Step"""
        # Your logic here

class ProcessOrderStep:
    def process(self, client, context) -> None:
        """Process Order Step"""
        # Your logic here


# Build and run pipeline
pipeline = Pipeline(
    ValidateOrderStep(),
    ProcessOrderStep(),
)

```

## CLI Commands

The SDK provides the `swoext` CLI for running and managing extensions:

### Run Extension

Start the extension server:

```bash
swoext run [OPTIONS]
```

**Options:**
- `--bind ADDRESS` - Bind address (default: `0.0.0.0:8080`)
- `--debug` - Enable debug mode
- `--color / --no-color` - Enable/disable colored output
- `--reload` - Enable auto-reload on code changes (development)

**Example:**
```bash
swoext run --bind 0.0.0.0:8080 --debug --reload
```

### Run Event Consumer

Start the event consumer to process MPT events:

```bash
swoext run --events
```

### Django Management Commands

Access Django management commands:

```bash
swoext django <command> [args]
```


## Integrations

### OpenTelemetry Integration

Built-in observability with OpenTelemetry:

- **Distributed Tracing**: Track requests across services
- **Logging Instrumentation**: Structured logging with trace context
-
**Configuration:**
```bash
# Enable Application Insights
USE_APPLICATIONINSIGHTS=true
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
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

**Action Required:** Update your `MPT_API_BASE_URL` configuration to remove any version path suffixes.


## Development

For development setup, contribution guidelines, and advanced topics, see the [README](https://github.com/softwareone-platform/mpt-extension-sdk/blob/main/README.md) in the GitHub repository.
