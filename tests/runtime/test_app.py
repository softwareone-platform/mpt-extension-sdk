import asyncio
from types import ModuleType

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mpt_extension_sdk import APIRouter, EventRouter, Plug, PlugRouter
from mpt_extension_sdk.api import APIResponse
from mpt_extension_sdk.errors.runtime import ConfigError
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.routing import RouteType, ScheduleRouteDefinition
from mpt_extension_sdk.runtime import app as runtime_app


def runtime_plug_provider():
    return [
        Plug(
            id="adobe",
            name="Adobe",
            description="Adobe widget",
            socket="commerce.agreements.agreement",
            href="main-menu.js",
        )
    ]


@pytest.fixture
def extension_runtime_app(dummy_handler):
    router = EventRouter(prefix="/events/orders")
    router.event(path="/purchase", name="purchase", event="OrderPurchased")(dummy_handler)
    extension_app = ExtensionApp(prefix="/api/v1")
    extension_app.include_router(router)

    return extension_app


@pytest.fixture
def runtime_app_patches(mocker, extension_runtime_app):
    return {
        "setup_logging": mocker.patch("mpt_extension_sdk.runtime.app.setup_logging", autospec=True),
        "load_extension_app": mocker.patch(
            "mpt_extension_sdk.runtime.app.load_extension_app",
            autospec=True,
            return_value=extension_runtime_app,
        ),
        "bootstrap": mocker.patch(
            "mpt_extension_sdk.runtime.app.ObservabilityBootstrap.bootstrap", autospec=True
        ),
        "instrument_fastapi_app": mocker.patch(
            "mpt_extension_sdk.runtime.app.ObservabilityBootstrap.instrument_fastapi_app",
            autospec=True,
        ),
    }


@pytest.fixture
def middleware_test_app():
    app = runtime_app._create_fastapi_app(ExtensionApp())
    runtime_app._configure_middlewares(app)

    @app.get("/dummy")
    def dummy():  # noqa: WPS430
        return {"status": "ok"}

    return app


@pytest.fixture
def api_extension_app():
    api_router = APIRouter(prefix="/auth")
    extension_app = ExtensionApp(prefix="/api/v1")

    @api_router.get(path="/fake", name="fake")
    def wrapper(ctx):
        return APIResponse.ok(payload={"ok": bool(ctx)})

    extension_app.include_router(api_router)
    return extension_app


@pytest.fixture
def plug_extension_app():
    extension_app = ExtensionApp(prefix="/api/v1")
    plug_router = PlugRouter()
    plug_router.register()(runtime_plug_provider)
    extension_app.include_router(plug_router)
    return extension_app


def test_load_ext_app_rejects_empty_module_name():
    with pytest.raises(ConfigError, match="Extension app module cannot be empty"):
        runtime_app.load_extension_app("")


def test_load_ext_app_requires_ext_app(mocker):
    module = ModuleType("tests.fake_app_missing")
    mocker.patch("mpt_extension_sdk.runtime.app.import_module", autospec=True, return_value=module)

    with pytest.raises(ConfigError, match="must export 'ext_app'"):
        runtime_app.load_extension_app("tests.fake_app_missing")


def test_load_ext_app_requires_ext_app_instance(mocker):
    module = ModuleType("tests.fake_app_invalid")
    module.ext_app = object()
    mocker.patch("mpt_extension_sdk.runtime.app.import_module", autospec=True, return_value=module)

    with pytest.raises(ConfigError, match="must be an ExtensionApp"):
        runtime_app.load_extension_app("tests.fake_app_invalid")


def test_load_ext_app_returns_exported_app(mocker):
    module = ModuleType("tests.fake_app_valid")
    module.ext_app = ExtensionApp()
    mocker.patch("mpt_extension_sdk.runtime.app.import_module", autospec=True, return_value=module)

    result = runtime_app.load_extension_app("tests.fake_app_valid")

    assert result is module.ext_app


def test_create_runtime_app_bootstraps_deps(runtime_settings, runtime_app_patches):
    setup_logging = runtime_app_patches["setup_logging"]
    load_extension_app = runtime_app_patches["load_extension_app"]
    bootstrap = runtime_app_patches["bootstrap"]
    instrument_fastapi_app = runtime_app_patches["instrument_fastapi_app"]

    result = runtime_app.create_runtime_app(runtime_settings)

    assert result.version == runtime_app_patches["load_extension_app"].return_value.version
    setup_logging.assert_called_once_with(
        runtime_settings.log_level, runtime_settings.extension_package
    )
    load_extension_app.assert_called_once_with(runtime_settings.app_module)
    bootstrap.assert_called_once()
    instrument_fastapi_app.assert_called_once()


def test_create_runtime_app_registers_health(runtime_settings, runtime_app_patches):
    extension_app = runtime_app_patches["load_extension_app"].return_value

    result = runtime_app.create_runtime_app(runtime_settings)

    response = TestClient(result).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": extension_app.version}


def test_create_runtime_app_registers_live(runtime_settings, runtime_app_patches):
    result = runtime_app.create_runtime_app(runtime_settings)

    response = TestClient(result).get("/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_unavailable_before_startup(runtime_settings, runtime_app_patches):
    result = runtime_app.create_runtime_app(runtime_settings)

    response = TestClient(result).get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


async def _run_lifespan_with_wrapper(app: FastAPI) -> bool:
    # mrok's proxy passes its own ASGIAppWrapper (without `state`) here
    async with app.router.lifespan_context(object()):
        return app.state.ready


def test_lifespan_with_wrapper_argument():
    result = runtime_app._create_fastapi_app(ExtensionApp())

    assert asyncio.run(_run_lifespan_with_wrapper(result)) is True
    assert result.state.ready is False


def test_ready_follows_app_lifespan(runtime_settings, runtime_app_patches):
    result = runtime_app.create_runtime_app(runtime_settings)

    with TestClient(result) as client:
        started_response = client.get("/ready")
    stopped_response = TestClient(result).get("/ready")
    assert started_response.status_code == 200
    assert started_response.json() == {"status": "ok"}
    assert stopped_response.status_code == 503
    assert stopped_response.json() == {"status": "unavailable"}


def test_create_runtime_app_registers_ext_routes(runtime_settings, runtime_app_patches):
    result = runtime_app.create_runtime_app(runtime_settings)

    assert "/api/v1/events/orders/purchase" in {route.path for route in result.routes}


def test_create_runtime_app_mounts_static(runtime_settings, runtime_app_patches):
    result = runtime_app.create_runtime_app(runtime_settings)

    assert "/static" in {route.path for route in result.routes}


def test_register_ext_routes(dummy_handler):
    app = FastAPI()
    extension_app = ExtensionApp(prefix="/api/v1")
    router = EventRouter(prefix="/events/orders")
    router.event(path="/purchase", name="purchase", event="OrderPurchased")(dummy_handler)
    router.task(path="/change", name="change", event="OrderChanged")(dummy_handler)
    extension_app.include_router(router)

    runtime_app.register_extension_routes(app, extension_app)  # act

    paths = {route.path for route in app.routes}
    assert "/api/v1/events/orders/purchase" in paths
    assert "/api/v1/events/orders/change" in paths


def test_register_api_ext_routes(api_extension_app):
    app = FastAPI()

    runtime_app.register_extension_routes(app, api_extension_app)  # act

    api_route = next(route for route in app.routes if route.path == "/api/v1/auth/fake")
    assert "GET" in api_route.methods


def test_register_ext_routes_ignores_plugs(plug_extension_app):
    app = FastAPI()

    runtime_app.register_extension_routes(app, plug_extension_app)  # act

    assert all(route.path != "/api/v1/plug_provider" for route in app.routes)


def test_register_not_supported_ext_routes(dummy_handler):
    app = FastAPI()
    extension_app = ExtensionApp(prefix="/api/v1")
    extension_app._routes.append(
        ScheduleRouteDefinition(
            path="/cron", name="cron", route_type=RouteType.SCHEDULE, callback=dummy_handler
        )
    )

    with pytest.raises(ConfigError, match="Only event, api, and plug routes are supported"):
        runtime_app.register_extension_routes(app, extension_app)


def test_middlewares_propagate_request_headers(middleware_test_app):
    result = TestClient(middleware_test_app).get(
        "/dummy", headers={"x-request-id": "req-1", "mpt-task-id": "task-1"}
    )

    assert result.status_code == 200
    assert result.headers["x-request-id"] == "req-1"
    assert result.headers["mpt-task-id"] == "task-1"
