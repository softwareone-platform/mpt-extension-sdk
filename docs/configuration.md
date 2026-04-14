# Configuration

This document describes repository-specific runtime configuration exposed by the SDK.

## Core Environment Variables

The SDK runtime relies on these settings:

| Variable | Default | Example | Description |
| --- | --- | --- | --- |
| `EXT_WEBHOOKS_SECRETS` | - | `{"PRD-1111-1111":"secret"}` | Webhook secret mapping keyed by Marketplace product id |
| `MPT_API_BASE_URL` | `http://localhost:8000` | `https://api.s1.show` | SoftwareONE Marketplace API base URL |
| `MPT_API_TOKEN` | - | `eyJhbGciOi...` | SoftwareONE Marketplace API token |
| `MPT_PRODUCTS_IDS` | `PRD-1111-1111` | `PRD-1111-1111,PRD-2222-2222` | Comma-separated Marketplace product ids |
| `MPT_PORTAL_BASE_URL` | `https://portal.s1.show` | `https://portal.s1.show` | Marketplace portal base URL |
| `MPT_ORDERS_API_POLLING_INTERVAL_SECS` | `120` | `60` | Orders polling interval in seconds |

## Example Environment

```dotenv
EXT_WEBHOOKS_SECRETS={"PRD-1111-1111":"<webhook-secret-for-product>","PRD-2222-2222":"<webhook-secret-for-product>"}
MPT_API_BASE_URL=https://api.s1.show
MPT_API_TOKEN=<your-api-token>
MPT_PRODUCTS_IDS=PRD-1111-1111,PRD-2222-2222
MPT_PORTAL_BASE_URL=https://portal.s1.show
```

## Runtime Notes

- [`mpt_extension_sdk/runtime/initializer.py`](../mpt_extension_sdk/runtime/initializer.py) normalizes selected extension variables and initializes Django settings.
- [`mpt_extension_sdk/runtime/djapp/apps.py`](../mpt_extension_sdk/runtime/djapp/apps.py) fails startup when required webhook secrets are missing for configured product ids.
- [`docs/migrations.md`](migrations.md) documents the `MPT_API_BASE_URL` compatibility change for `/public/v1/`.

## Observability

Application Insights support is controlled through Django settings consumed during runtime initialization. A typical setup includes:

```bash
USE_APPLICATIONINSIGHTS=true
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
```

Document additional repository-specific configuration here when SDK runtime requirements expand.
