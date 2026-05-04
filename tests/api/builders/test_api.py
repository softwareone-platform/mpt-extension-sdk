from contextlib import contextmanager
from http import HTTPStatus

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import Field

from mpt_extension_sdk.api import APIResponse, ForbiddenError, PaginatedResult
from mpt_extension_sdk.api.auth import AccountType
from mpt_extension_sdk.api.builders.api import create_api_route
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.models.account import AccountToken
from mpt_extension_sdk.routing.routers import APIRouter
from mpt_extension_sdk.schemas import BaseSchema
from mpt_extension_sdk.services.mpt_api_service import AccountTokenProvider, MPTAPIService

ACCOUNT_TOKEN = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJleHAiOjQxMDI0NDQ4MDB9."
AUTH_TOKEN = (
    "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0."
    "eyJodHRwczovL2NsYWltcy5zb2Z0d2FyZW9uZS5jb20vYWNjb3VudElkIjoiQUNDLTEiLCJodHRwczov"
    "L2NsYWltcy5zb2Z0d2FyZW9uZS5jb20vYWNjb3VudFR5cGUiOiJDbGllbnQiLCJodHRwczovL2NsYWlt"
    "cy5zb2Z0d2FyZW9uZS5jb20vZXh0ZW5zaW9uSWQiOiJFWFQtMSIsImh0dHBzOi8vY2xhaW1zLnNvZnR3"
    "YXJlb25lLmNvbS9tb2R1bGVzIjp7ImJpbGxpbmciOlsiZWRpdCJdfSwiaXNzIjoiaHR0cHM6Ly9tcHQt"
    "ZXh0ZW5zaW9ucy5zb2Z0d2FyZW9uZS5jb20iLCJleHAiOjQxMDI0NDQ4MDB9."
)
MALFORMED_AUTH_TOKEN = "not-a-jwt"
VENDOR_AUTH_TOKEN = (
    "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0."
    "eyJodHRwczovL2NsYWltcy5zb2Z0d2FyZW9uZS5jb20vYWNjb3VudElkIjoiQUNDLTEiLCJodHRwczov"
    "L2NsYWltcy5zb2Z0d2FyZW9uZS5jb20vYWNjb3VudFR5cGUiOiJWZW5kb3IiLCJodHRwczovL2NsYWlt"
    "cy5zb2Z0d2FyZW9uZS5jb20vZXh0ZW5zaW9uSWQiOiJFWFQtMSIsImh0dHBzOi8vY2xhaW1zLnNvZnR3"
    "YXJlb25lLmNvbS9tb2R1bGVzIjp7fSwiaXNzIjoiaHR0cHM6Ly9tcHQtZXh0ZW5zaW9ucy5zb2Z0d2Fy"
    "ZW9uZS5jb20iLCJleHAiOjQxMDI0NDQ4MDB9."
)
EXPIRED_AUTH_TOKEN = (
    "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0."
    "eyJodHRwczovL2NsYWltcy5zb2Z0d2FyZW9uZS5jb20vYWNjb3VudElkIjogIkFDQy0xIiwgImh0dHBz"
    "Oi8vY2xhaW1zLnNvZnR3YXJlb25lLmNvbS9hY2NvdW50VHlwZSI6ICJDbGllbnQiLCAiaHR0cHM6Ly9j"
    "bGFpbXMuc29mdHdhcmVvbmUuY29tL2V4dGVuc2lvbklkIjogIkVYVC0xIiwgImh0dHBzOi8vY2xhaW1z"
    "LnNvZnR3YXJlb25lLmNvbS9tb2R1bGVzIjogeyJiaWxsaW5nIjogWyJlZGl0Il19LCAiaXNzIjogImh0"
    "dHBzOi8vbXB0LWV4dGVuc2lvbnMuc29mdHdhcmVvbmUuY29tIiwgImV4cCI6IDEwMDAwMDAwMDB9."
)
EMPTY_ACCOUNT_TOKEN = (
    "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0."
    "eyJodHRwczovL2NsYWltcy5zb2Z0d2FyZW9uZS5jb20vYWNjb3VudElkIjogIiIsICJodHRwczovL2Ns"
    "YWltcy5zb2Z0d2FyZW9uZS5jb20vYWNjb3VudFR5cGUiOiAiQ2xpZW50IiwgImh0dHBzOi8vY2xhaW1z"
    "LnNvZnR3YXJlb25lLmNvbS9leHRlbnNpb25JZCI6ICJFWFQtMSIsICJodHRwczovL2NsYWltcy5zb2Z0"
    "d2FyZW9uZS5jb20vbW9kdWxlcyI6IHsiYmlsbGluZyI6IFsiZWRpdCJdfSwgImlzcyI6ICJodHRwczov"
    "L21wdC1leHRlbnNpb25zLnNvZnR3YXJlb25lLmNvbSIsICJleHAiOiA0MTAyNDQ0ODAwfQ."
)


class FakeAgreementSchema(BaseSchema):
    """Request payload used by authenticated API builder tests."""

    status: str = Field(pattern="^(Processing|Complete)$")


def query_helpers_handler(ctx):
    return APIResponse.ok(
        payload={
            "include_closed": ctx.request.query.get_bool("include_closed"),
            "limit": ctx.request.query.get_int("limit"),
            "tags": ctx.request.query.get_list("tag"),
            "fallback": ctx.request.query.get_bool("fallback", default=False),
            "malformed": ctx.request.query.get_bool("malformed", default=True),
        }
    )


def invalid_query_int_handler(ctx):
    ctx.request.query.get_int("limit")
    return APIResponse.no_content()


def body_echo_handler(ctx):
    return APIResponse.ok(payload=ctx.request.body)


def paginated_orders_handler(ctx):
    pagination = ctx.request.pagination
    return APIResponse.paginated(
        PaginatedResult.from_pagination(
            pagination,
            payload=[{"id": "ORD-1"}, {"id": "ORD-2"}],
            total=5,
        )
    )


def invalid_pagination_handler(ctx):
    return APIResponse.ok(payload={"page": ctx.request.pagination.page})


@pytest.fixture(autouse=True)
def clear_account_token_cache():
    AccountTokenProvider.clear_cache()
    yield
    AccountTokenProvider.clear_cache()


@pytest.fixture
def auth_token():
    return AUTH_TOKEN


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def account_token():
    return AccountToken(
        token=ACCOUNT_TOKEN,
        exp="4102444800",
    )


@pytest.fixture
def mock_api_service(mocker, account_token):
    fake_service = mocker.AsyncMock(spec=MPTAPIService)
    fake_service.installations = mocker.AsyncMock()
    fake_service.installations.create_token = mocker.AsyncMock(return_value=account_token)
    return fake_service


@pytest.fixture
def api_service_type_factory():
    def factory(fake_service):
        class FakeAPIService(MPTAPIService):  # noqa: WPS431
            @classmethod
            def from_config(cls, base_url: str, api_token: str):
                return fake_service

        return FakeAPIService

    return factory


@pytest.fixture
def api_route_dependencies(mocker, runtime_settings):
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_runtime_settings",
        autospec=True,
        return_value=runtime_settings,
    )
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_extension_settings",
        autospec=True,
        return_value=mocker.sentinel.extension_settings,
    )


@pytest.fixture
def api_app_factory(api_service_type_factory, mock_api_service):
    def factory(
        *,
        route_handler,
        method="get",
        prefix="/auth",
        path="/check",
        name="auth-check",
        body_validator=None,
    ):
        extension_app = ExtensionApp(
            mpt_api_service_type=api_service_type_factory(mock_api_service)
        )
        api_router = APIRouter(prefix=prefix)
        route_factory = getattr(api_router, method)
        route_kwargs = {"path": path, "name": name}
        if body_validator is not None:
            route_kwargs["body_validator"] = body_validator
        route_factory(**route_kwargs)(route_handler)
        extension_app.include_router(api_router)
        app = FastAPI()
        app.include_router(create_api_route(extension_app.routes[0], extension_app))
        return TestClient(app)

    return factory


@pytest.fixture
def ok_handler():
    def wrapper(ctx):
        return APIResponse.ok(payload={"ok": True})

    return wrapper


@pytest.fixture
def forbidden_handler():
    def wrapper(ctx, **kwargs):
        raise ForbiddenError("Only client accounts are supported")

    return wrapper


@pytest.fixture
def create_handler():
    def wrapper(agreement_id, agreement, ctx):
        return APIResponse.ok(payload={"id": agreement_id, "status": agreement.status})

    return wrapper


@pytest.fixture
def agreement_sync_handler(mocker):
    route_mock = mocker.Mock(
        return_value=APIResponse.created(payload={"id": "AGR-1", "status": "Processing"})
    )

    def wrapper(agreement_id, agreement, ctx):
        return route_mock(agreement_id=agreement_id, agreement=agreement, ctx=ctx)

    return wrapper, route_mock


@pytest.fixture
def api_span_mock(mocker):
    span = mocker.Mock()

    @contextmanager
    def wrapper(**kwargs):
        yield span

    start_api_span = mocker.patch(
        "mpt_extension_sdk.api.builders.api.start_api_span",
        autospec=True,
        side_effect=wrapper,
    )
    return start_api_span, span


def test_api_route_passes_context_and_body(  # noqa: WPS210, WPS218
    mocker,
    api_route_dependencies,
    auth_headers,
    api_app_factory,
    agreement_sync_handler,
    mock_api_service,
):
    mock_api_service.orders = mocker.sentinel.orders_service
    route_handler, route_mock = agreement_sync_handler
    client = api_app_factory(
        route_handler=route_handler,
        method="post",
        prefix="/agreements",
        path="/{agreement_id}/sync",
        name="agreement-sync",
        body_validator=FakeAgreementSchema,
    )

    result = client.post(
        "/agreements/AGR-1/sync?foo=bar",
        json={"status": "Processing"},
        headers=auth_headers,
    )

    assert result.status_code == HTTPStatus.CREATED
    assert result.json() == {"data": {"id": "AGR-1", "status": "Processing"}}
    route_mock.assert_called_once()
    arguments = route_mock.call_args.kwargs
    request_context = arguments["ctx"]
    assert arguments["agreement_id"] == "AGR-1"
    assert arguments["agreement"].status == "Processing"
    assert request_context.auth.account.id == "ACC-1"
    assert request_context.auth.account.type is AccountType.CLIENT
    assert request_context.auth.account.is_client() is True
    assert request_context.request.method == "POST"
    assert request_context.request.query.get("foo") == "bar"
    assert request_context.request.body == {"status": "Processing"}
    assert request_context.mpt_api_service.orders is mocker.sentinel.orders_service


def test_api_route_starts_observability_span(
    api_route_dependencies,
    auth_headers,
    api_app_factory,
    ok_handler,
    api_span_mock,
):
    start_api_span, _ = api_span_mock
    client = api_app_factory(route_handler=ok_handler)

    result = client.get(
        "/auth/check",
        headers={**auth_headers, "x-request-id": "corr-1"},
    )

    assert result.status_code == HTTPStatus.OK
    start_api_span.assert_called_once_with(
        route_name="auth-check",
        route_path="/auth/check",
        method="GET",
        account_id="ACC-1",
        extension_id="EXT-1",
        correlation_id="",
    )


def test_api_route_records_handler_error_on_span(
    mocker,
    api_route_dependencies,
    auth_headers,
    api_app_factory,
    api_span_mock,
    forbidden_handler,
):
    _, span = api_span_mock
    record_exception = mocker.patch(
        "mpt_extension_sdk.api.builders.api.record_exception", autospec=True
    )
    client = api_app_factory(route_handler=forbidden_handler)

    result = client.get("/auth/check", headers=auth_headers)

    assert result.status_code == HTTPStatus.FORBIDDEN
    record_exception.assert_called_once()
    assert record_exception.call_args.args[0] is span


def test_api_route_rejects_malformed_token(ok_handler, api_app_factory):
    client = api_app_factory(route_handler=ok_handler)
    headers = {"Authorization": f"Bearer {MALFORMED_AUTH_TOKEN}"}

    result = client.get("/auth/check", headers=headers)

    assert result.status_code == HTTPStatus.UNAUTHORIZED
    assert result.headers["content-type"].startswith("application/problem+json")
    assert result.json()["title"] == "Unauthorized"


def test_api_route_maps_body_errors(
    api_route_dependencies,
    mock_api_service,
    auth_headers,
    create_handler,
    api_app_factory,
):
    client = api_app_factory(
        route_handler=create_handler,
        method="post",
        prefix="/agreements",
        path="/{agreement_id}",
        name="agreement-create",
        body_validator=FakeAgreementSchema,
    )

    result = client.post(
        "/agreements/AGR-1",
        json={"status": "Invalid"},
        headers=auth_headers,
    )

    assert result.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert result.json()["title"] == "Validation failed"
    assert result.json()["errors"] == [
        {
            "detail": "String should match pattern '^(Processing|Complete)$'",
            "pointer": "#/status",
        }
    ]
    mock_api_service.installations.create_token.assert_not_awaited()


def test_api_route_exposes_typed_query_helpers(
    api_route_dependencies, auth_headers, api_app_factory
):
    client = api_app_factory(
        route_handler=query_helpers_handler,
        prefix="/adobe",
        path="/orders",
        name="adobe-orders",
    )

    result = client.get(
        "/adobe/orders?include_closed=YES&limit=25&tag=a&tag=b&malformed=not-a-bool",
        headers=auth_headers,
    )

    assert result.status_code == HTTPStatus.OK
    assert result.json()["data"] == {
        "include_closed": True,
        "limit": 25,
        "tags": ["a", "b"],
        "fallback": False,
        "malformed": True,
    }


def test_api_route_maps_invalid_query_int_errors(
    api_route_dependencies, auth_headers, api_app_factory
):
    client = api_app_factory(
        route_handler=invalid_query_int_handler,
        prefix="/adobe",
        path="/orders",
        name="adobe-orders",
    )

    result = client.get(
        "/adobe/orders?limit=abc",
        headers=auth_headers,
    )

    assert result.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert result.json()["errors"] == [
        {
            "detail": "Value must be an integer",
            "pointer": "#/limit",
        }
    ]


def test_api_route_exposes_body_without_validator(
    api_route_dependencies, auth_headers, api_app_factory
):
    request_body = {"external_id": "EXT-ORDER-1"}
    client = api_app_factory(
        route_handler=body_echo_handler,
        method="post",
        prefix="/adobe",
        path="/orders",
        name="adobe-orders",
    )

    result = client.post(
        "/adobe/orders",
        json=request_body,
        headers=auth_headers,
    )

    assert result.status_code == HTTPStatus.OK
    assert result.json()["data"] == request_body


def test_api_route_maps_invalid_json_body_errors(
    api_route_dependencies, auth_headers, api_app_factory, ok_handler
):
    client = api_app_factory(
        route_handler=ok_handler,
        method="post",
        prefix="/adobe",
        path="/orders",
        name="adobe-orders",
    )

    result = client.post(
        "/adobe/orders",
        content="{invalid",
        headers=auth_headers,
    )

    assert result.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert result.json()["errors"] == [
        {
            "detail": "Invalid JSON payload",
            "pointer": "#",
        }
    ]


def test_create_api_route_maps_api_errors(
    api_route_dependencies, api_app_factory, forbidden_handler
):
    client = api_app_factory(
        route_handler=forbidden_handler,
        method="post",
        prefix="/agreements",
        path="/{agreement_id}/sync",
        name="agreement-sync",
    )

    result = client.post(
        "/agreements/AGR-1/sync", headers={"Authorization": f"Bearer {VENDOR_AUTH_TOKEN}"}
    )

    assert result.status_code == HTTPStatus.FORBIDDEN
    assert result.json()["detail"] == "Only client accounts are supported"


def test_create_api_route_caches_account_tokens(
    api_route_dependencies,
    mock_api_service,
    auth_headers,
    ok_handler,
    api_app_factory,
):
    client = api_app_factory(route_handler=ok_handler)

    result = [
        client.get("/auth/check", headers=auth_headers),
        client.get("/auth/check", headers=auth_headers),
    ]

    first_response, second_response = result
    assert first_response.status_code == HTTPStatus.OK
    assert second_response.status_code == HTTPStatus.OK
    mock_api_service.installations.create_token.assert_awaited_once()


def test_api_route_rejects_expired_token(ok_handler, api_app_factory):
    client = api_app_factory(route_handler=ok_handler)

    result = client.get("/auth/check", headers={"Authorization": f"Bearer {EXPIRED_AUTH_TOKEN}"})

    assert result.status_code == HTTPStatus.UNAUTHORIZED
    assert result.json()["title"] == "Unauthorized"


def test_api_route_rejects_mismatched_ext_id(api_route_dependencies, ok_handler, api_app_factory):
    mismatched_token = (
        "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0."
        "eyJodHRwczovL2NsYWltcy5zb2Z0d2FyZW9uZS5jb20vYWNjb3VudElkIjoiQUNDLTEiLCJodHRwczov"
        "L2NsYWltcy5zb2Z0d2FyZW9uZS5jb20vYWNjb3VudFR5cGUiOiJDbGllbnQiLCJodHRwczovL2NsYWlt"
        "cy5zb2Z0d2FyZW9uZS5jb20vZXh0ZW5zaW9uSWQiOiJFWFQtMiIsImh0dHBzOi8vY2xhaW1zLnNvZnR3"
        "YXJlb25lLmNvbS9tb2R1bGVzIjp7ImJpbGxpbmciOlsiZWRpdCJdfSwiaXNzIjoiaHR0cHM6Ly9tcHQt"
        "ZXh0ZW5zaW9ucy5zb2Z0d2FyZW9uZS5jb20iLCJleHAiOjQxMDI0NDQ4MDB9."
    )
    client = api_app_factory(route_handler=ok_handler)

    result = client.get("/auth/check", headers={"Authorization": f"Bearer {mismatched_token}"})

    assert result.status_code == HTTPStatus.UNAUTHORIZED
    assert result.json()["title"] == "Unauthorized"


def test_api_route_rejects_empty_account_id(ok_handler, api_app_factory):
    client = api_app_factory(route_handler=ok_handler)

    result = client.get("/auth/check", headers={"Authorization": f"Bearer {EMPTY_ACCOUNT_TOKEN}"})

    assert result.status_code == HTTPStatus.UNAUTHORIZED
    assert result.json()["title"] == "Unauthorized"


def test_api_route_builds_paginated_response(api_route_dependencies, auth_headers, api_app_factory):
    client = api_app_factory(
        route_handler=paginated_orders_handler,
        prefix="/adobe",
        path="/orders",
        name="adobe-orders",
    )

    result = client.get(
        "/adobe/orders?page=2&page_size=2&filter=open",
        headers=auth_headers,
    )

    assert result.status_code == HTTPStatus.OK
    assert result.json() == {
        "data": [{"id": "ORD-1"}, {"id": "ORD-2"}],
        "meta": {"total": 5, "page": 2, "page_size": 2, "total_pages": 3},
        "links": {
            "self": "http://testserver/adobe/orders?filter=open&page=2&page_size=2",
            "first": "http://testserver/adobe/orders?filter=open&page=1&page_size=2",
            "prev": "http://testserver/adobe/orders?filter=open&page=1&page_size=2",
            "next": "http://testserver/adobe/orders?filter=open&page=3&page_size=2",
            "last": "http://testserver/adobe/orders?filter=open&page=3&page_size=2",
        },
    }


def test_api_route_maps_invalid_pagination_errors(
    api_route_dependencies, auth_headers, api_app_factory
):
    client = api_app_factory(
        route_handler=invalid_pagination_handler,
        prefix="/adobe",
        path="/orders",
        name="adobe-orders",
    )

    result = client.get(
        "/adobe/orders?page_size=999",
        headers=auth_headers,
    )

    assert result.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert result.json()["errors"] == [
        {
            "detail": "Value must be less than or equal to 500",
            "pointer": "#/page_size",
        }
    ]
