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
`EventRouter`, `APIRouter`, and `ScheduleRouter` are mounted by the runtime.
`PlugRouter` is declarative: its plug definitions are emitted into metadata and
its static assets are exposed through `/static`.

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

## Run Code At Runtime Startup

Register process-wide initialization with `ExtensionApp.on_startup`. Hooks run
once per served process, after the SDK bootstraps observability and before the
app reports itself as ready:

```python
from mpt_extension_sdk import ExtensionApp

ext_app = ExtensionApp(prefix="/api/v2")


@ext_app.on_startup
def warm_up_caches() -> None:
    """Prepare process-wide state before the app serves traffic."""
    ...


@ext_app.on_startup
async def open_vendor_session() -> None:
    """Async hooks are awaited."""
    ...
```

Hooks take no arguments; sync and async callables are both supported, and they
run in registration order. `on_startup` returns the hook, so it also works as a
decorator. Hooks run only when the runtime serves the extension
(`mpt-ext run`) — metadata generation (`mpt-ext meta generate` /
`meta validate`) never invokes them. Metadata generation does import `app.py`
and call registered plug providers to build `meta.yaml`, so it is not free of
extension code; startup hooks are simply not part of it. That makes
`on_startup` the place for side effects that must stay out of module import,
such as extra OpenTelemetry instrumentation (see
[observability.md](observability.md#adding-other-instrumentation)).

Registering no hooks keeps the previous startup behavior unchanged.

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
