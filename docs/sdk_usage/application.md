# Application Setup

## Install The SDK

Install the package in a consumer project:

```bash
pip install mpt-extension-sdk
```

```bash
uv add mpt-extension-sdk
```

## Extension Package Shape

The runtime auto-discovers exactly one top-level package in the working directory. That package
must export:

- `app.py` with `ext_app`
- `settings.py` with `ExtensionSettings`

`ExtensionSettings` must inherit from
`mpt_extension_sdk.settings.extension.BaseExtensionSettings`.

Keep imports in `app.py` deterministic. The runtime imports `ext_app` to build
metadata before startup, so avoid network calls, filesystem I/O, or other heavy
side effects at module import time.

## Create An Extension App

Start with `ExtensionApp` and the router family that matches your use case. The
extension app is the root SDK object for one extension package.

```python
# mock_app/app.py
from mpt_extension_sdk import ExtensionApp

from mock_app.api.routes.event import orders_router

ext_app = ExtensionApp(prefix="/api/v2")
ext_app.include_router(orders_router)
```

```python
# mock_app/api/routes/event.py
from mpt_extension_sdk.routing import EventRouter

orders_router = EventRouter(prefix="/events/orders")
```

The SDK also exposes `APIRouter`, `ScheduleRouter`, and `PlugRouter`.
`EventRouter` and `APIRouter` are mounted by the runtime. `PlugRouter` is
declarative: its plug definitions are emitted into metadata and its static
assets are exposed through `/static`. `ScheduleRouter` is modeled in the SDK
contract but is not yet mounted by the runtime or emitted into metadata.

## Include Multiple Routers

Include each router in the extension app:

```python
from mpt_extension_sdk import ExtensionApp

from mock_app.api.routes.api import api_router
from mock_app.api.routes.event import orders_router

ext_app = ExtensionApp(prefix="/api/v2")
ext_app.include_router(api_router)
ext_app.include_router(orders_router)
```

## Configure The Runtime

The SDK commonly relies on:

- `SDK_EXTENSION_URL`
- `SDK_EXTENSION_API_KEY`
- `SDK_EXTENSION_ID`
- `MPT_API_BASE_URL`

Example configuration:

```dotenv
SDK_EXTENSION_URL=https://extensions.example.com
SDK_EXTENSION_API_KEY=<extension-api-key>
SDK_EXTENSION_ID=EXT-1234
MPT_API_BASE_URL=https://api.s1.show
SDK_LOCAL_PORT=8080
```

`BaseExtensionSettings` also inherits shared helpers for custom environment
variables:

- `bool_env()` parses boolean flags such as `true`, `1`, and `yes`.
- `int_env()` parses integers and raises `ConfigError` for invalid values.
- `list_env()` parses comma-separated strings into trimmed lists.
- `json_env()` parses JSON objects, arrays, and scalar values and raises
  `ConfigError` for invalid JSON.

See [configuration.md](../configuration.md) for the runtime environment-variable reference.
