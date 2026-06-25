# Settings

The SDK separates configuration into three layers with different
responsibilities. All three are injected into every execution context, so
handlers, pipeline steps, and services read configuration from the context
instead of loading environment variables directly.

| Layer | Context attribute | Type | Owner |
| --- | --- | --- | --- |
| Runtime settings | `ctx.runtime_settings` | `RuntimeSettings` | SDK |
| Extension settings | `ctx.ext_settings` | `ExtensionSettings` (your subclass) | Extension |
| Account settings | `ctx.account_settings` | `AccountSettings` | Platform (future) |

## Runtime Settings

`RuntimeSettings` is SDK-owned, frozen, and loaded exclusively from environment
variables. It carries infrastructure-level configuration such as the platform
endpoints, local runtime host/port, observability flags, and the autodiscovered
extension package modules.

Extensions consume it read-only:

```python
log_level = ctx.runtime_settings.log_level
extension_id = ctx.runtime_settings.extension_id
```

The process-wide singleton is available through `get_runtime_settings()` and is
cached with `functools.lru_cache`. The required environment variables
(`SDK_EXTENSION_URL`, `SDK_EXTENSION_API_KEY`, `SDK_EXTENSION_ID`,
`MPT_API_BASE_URL`) are validated on load and raise `ConfigError` when missing.
See [configuration.md](../configuration.md) for the full environment-variable
reference.

## Extension Settings

Each extension defines its own settings model by subclassing
`BaseExtensionSettings`. This is where vendor credentials, API base URLs,
product mappings, and feature flags live.

`settings.py` at the root of the extension package must export a class named
`ExtensionSettings`. The SDK autodiscovers it, calls `ExtensionSettings.load()`,
and caches the result for the process.

```python
# mock_app/settings.py
import os
from dataclasses import dataclass
from typing import Self, override

from mpt_extension_sdk.settings.extension import BaseExtensionSettings


@dataclass(frozen=True)
class ExtensionSettings(BaseExtensionSettings):
    adobe_api_url: str
    adobe_client_id: str
    product_ids: list[str]

    @override
    @classmethod
    def load(cls) -> Self:
        return cls(
            adobe_api_url=os.getenv("ADOBE_API_URL", ""),
            adobe_client_id=os.getenv("ADOBE_CLIENT_ID", ""),
            product_ids=cls.list_env("PRODUCT_IDS"),
        )
```

Consume it from the context:

```python
product_ids = ctx.ext_settings.product_ids
```

### Environment-variable helpers

`BaseExtensionSettings` inherits shared parsing helpers from `BaseSettings`. Use
them inside `load()` instead of re-implementing parsing in business code:

- `bool_env(key, *, default)` parses `true`/`1`/`yes` (case-insensitive) as
  `True` and anything else as the boolean fallback.
- `int_env(key, *, default)` parses an integer and raises `ConfigError` on an
  invalid value.
- `list_env(key, *, default="")` splits a comma-separated string into a trimmed
  list, returning `[]` when unset.
- `json_env(key, *, default="{}")` parses JSON objects, arrays, and scalars and
  raises `ConfigError` on invalid JSON.

### Required-variable validation

Override `required_env_vars` to fail fast when a mandatory variable is missing.
Each entry is a `(value, message)` tuple; `validate()` runs automatically after
initialization and raises `ConfigError` listing every empty value.

```python
@property
@override
def required_env_vars(self) -> list[tuple[str, ...]]:
    return [
        (self.adobe_api_url, "ADOBE_API_URL is required"),
        (self.adobe_client_id, "ADOBE_CLIENT_ID is required"),
    ]
```

## Account Settings

`account_settings` is an account-scoped layer reserved for customer-specific
configuration that the platform model may provide in the future. The current
`AccountSettings` is an empty placeholder, so `ctx.account_settings` is always
present but carries no fields yet. Read from it for forward compatibility; do
not depend on specific account-level fields until the platform exposes them.
