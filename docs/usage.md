# SDK Usage

This guide shows how to build on top of `mpt-extension-sdk`.

## Install The SDK

Install the package in a consumer project:

```bash
pip install mpt-extension-sdk
```

```bash
uv add mpt-extension-sdk
```

## Create An Extension

Start with the `Extension` primitive. It gives you an event registry and an API surface.

```python
from mpt_extension_sdk.core.extension import Extension

ext = Extension()


@ext.events.listener("orders")
def process_order(client, event):
    """Process order events."""
```

## Add A Validation Endpoint

Use the built-in Ninja API when your extension needs HTTP endpoints.

```python
from mpt_extension_sdk.core.extension import Extension
from mpt_extension_sdk.core.security import JWTAuth

ext = Extension()


def jwt_secret_callback(client, claims):
    """Return the webhook secret used for JWT validation."""
    return "your-webhook-secret"


@ext.api.post("/v1/orders/validate", auth=JWTAuth(jwt_secret_callback))
def process_order_validation(request, order):
    """Validate an incoming order."""
    return {"status": "accepted"}
```

## Build A Processing Pipeline

Use `Pipeline` for multi-step processing flows.

```python
from mpt_extension_sdk.flows.pipeline import Pipeline


class ValidateOrderStep:
    def process(self, client, context) -> None:
        """Validate the order payload."""


class ProcessOrderStep:
    def process(self, client, context) -> None:
        """Run the main order logic."""


pipeline = Pipeline(
    ValidateOrderStep(),
    ProcessOrderStep(),
)
```

## Run An Extension

Use the `swoext` CLI when running an extension built on top of the SDK:

```bash
swoext run
swoext run api --debug --reload
swoext run consumer
swoext django <command>
swoext shell
```

## Configure The Runtime

The SDK commonly relies on:

- `MPT_API_BASE_URL`
- `MPT_API_TOKEN`
- `MPT_PRODUCTS_IDS`
- `EXT_WEBHOOKS_SECRETS`

Example configuration:

```dotenv
EXT_WEBHOOKS_SECRETS={"PRD-1111-1111":"<webhook-secret-for-product>"}
MPT_API_BASE_URL=https://api.s1.show
MPT_API_TOKEN=<your-api-token>
MPT_PRODUCTS_IDS=PRD-1111-1111
MPT_PORTAL_BASE_URL=https://portal.s1.show
```

Use `MPT_API_BASE_URL` without `/v1` or `/public/v1`. See [configuration.md](configuration.md) for the environment-variable reference and [migrations.md](migrations.md) for the compatibility note behind that rule.

## What The SDK Provides

- an `Extension` primitive with event listener registration and a Django Ninja API surface
- runtime wiring for the `swoext` CLI and packaged Django app configuration
- reusable helpers for Marketplace HTTP, Key Vault, Airtable, telemetry, and RQL concerns
- pipeline primitives for multi-step processing flows
