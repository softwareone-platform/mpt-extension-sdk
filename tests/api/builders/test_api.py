import asyncio
from contextlib import contextmanager
from http import HTTPStatus

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import Field

from mpt_extension_sdk.api import APIContext, APIResponse, ForbiddenError, PaginatedResult
from mpt_extension_sdk.api.auth import AccountType
from mpt_extension_sdk.api.builders.api import create_api_route
from mpt_extension_sdk.api.builders.arguments import APIHandlerArgumentsBuilder
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.routing import APIRouteDefinition, APIRouter, HTTPMethod, RouteType
from mpt_extension_sdk.runtime import app as runtime_app
from mpt_extension_sdk.schemas import BaseSchema
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService

MALFORMED_AUTH_TOKEN = "not-a-jwt"
EXPIRED_EXP_TIMESTAMP = 1000000000


class FakeAgreementSchema(BaseSchema):
    """Request payload used by authenticated API builder tests."""

    status: str = Field(pattern="^(Processing|Complete)$")


class OptionalAgreementSchema(BaseSchema):
    """Request payload with defaults used by empty-body tests."""

    status: str = "Processing"


def query_helpers_handler(ctx):
    return APIResponse.ok(
        payload={
            "contains_limit": "limit" in ctx.request.query,
            "first_tag": ctx.request.query["tag"],
            "include_closed": ctx.request.query.get_bool("include_closed"),
            "is_closed": ctx.request.query.get_bool("is_closed"),
            "limit": ctx.request.query.get_int("limit"),
            "missing_int": ctx.request.query.get_int("missing_int", default=15),
            "tags": ctx.request.query.get_list("tag"),
            "fallback": ctx.request.query.get_bool("fallback", default=False),
            "malformed": ctx.request.query.get_bool("malformed", default=True),
            "query": ctx.request.query.multi_items(),
        }
    )


def invalid_query_int_handler(ctx):
    ctx.request.query.get_int("limit")
    return APIResponse.no_content()


def body_echo_handler(ctx):
    return APIResponse.ok(payload=ctx.request.body)


def body_annotation_handler(agreement_id, ctx, payload: FakeAgreementSchema):
    return APIResponse.ok(payload={"id": agreement_id, "status": payload.status})


def ambiguous_body_handler(first, second, ctx):
    return APIResponse.ok(payload={"first": first, "second": second, "ctx": bool(ctx)})


def default_body_handler(payload, ctx):
    return APIResponse.ok(payload={"status": payload.status, "body": ctx.request.body})


def no_context_handler(order_id):
    return APIResponse.ok(payload={"id": order_id})


def paginated_orders_handler(ctx):
    pagination = ctx.request.pagination
    return APIResponse.paginated(
        PaginatedResult.from_pagination(
            pagination,
            payload=[{"id": "ORD-1"}, {"id": "ORD-2"}],
            total=5,
        )
    )


def invalid_response_handler(ctx):
    return {"ok": bool(ctx)}


def unhandled_error_handler(ctx):
    raise ValueError("Unexpected")


@pytest.fixture
def auth_token(auth_claims_factory, jwt_token_factory):
    return jwt_token_factory(auth_claims_factory(modules={"billing": ["edit"]}))


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def mock_api_service(mocker):
    return mocker.AsyncMock(spec=MPTAPIService)


@pytest.fixture
def api_service_type_factory(mocker):
    def factory(fake_service):
        class FakeAPIService(MPTAPIService):  # noqa: WPS431
            from_auth_context = mocker.AsyncMock(return_value=fake_service)

        fake_service.service_type = FakeAPIService
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
        runtime_app._configure_middlewares(app)
        app.include_router(create_api_route(extension_app.routes[0], extension_app))
        return TestClient(app)

    return factory


@pytest.fixture
def ok_handler():
    def wrapper(ctx):
        return APIResponse.ok(payload={"ok": True})

    return wrapper


@pytest.fixture
def ok_response_factory():
    return APIResponse.ok


@pytest.fixture
def async_ok_handler(ok_response_factory):
    async def wrapper(ctx):
        await asyncio.sleep(0)
        return ok_response_factory(payload={"ok": bool(ctx)})

    return wrapper


@pytest.fixture
def forbidden_handler():
    def wrapper(ctx, **kwargs):
        raise ForbiddenError("Only client accounts are supported")

    return wrapper


@pytest.fixture
def invalid_pagination_handler(ok_response_factory):
    def wrapper(ctx):
        return ok_response_factory(payload={"page": ctx.request.pagination.page})

    return wrapper


@pytest.fixture
def create_handler():
    def wrapper(agreement_id, agreement, ctx):
        return APIResponse.ok(payload={"id": agreement_id, "status": agreement.status})

    return wrapper


@pytest.fixture
def typed_context_handler(ok_response_factory):
    def wrapper(custom_ctx: APIContext):
        return ok_response_factory(payload={"method": custom_ctx.request.method})

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
        "mpt_extension_sdk.api.builders.execution.start_api_span",
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


def test_api_route_resolves_body_annotation(api_route_dependencies, auth_headers, api_app_factory):
    client = api_app_factory(
        route_handler=body_annotation_handler,
        method="post",
        prefix="/agreements",
        path="/{agreement_id}/sync",
        name="agreement-sync",
        body_validator=FakeAgreementSchema,
    )

    result = client.post(
        "/agreements/AGR-1/sync", json={"status": "Complete"}, headers=auth_headers
    )

    response_status = result.status_code
    assert response_status == HTTPStatus.OK
    assert result.json()["data"] == {"id": "AGR-1", "status": "Complete"}


def test_api_route_resolves_context_annotation(
    api_route_dependencies, auth_headers, api_app_factory, typed_context_handler
):
    client = api_app_factory(route_handler=typed_context_handler)

    result = client.get("/auth/check", headers=auth_headers)

    response_status = result.status_code
    assert response_status == HTTPStatus.OK
    assert result.json()["data"] == {"method": "GET"}


def test_api_route_rejects_ambiguous_body(api_route_dependencies, api_app_factory):
    with pytest.raises(TypeError, match="must expose exactly one body parameter"):
        api_app_factory(
            route_handler=ambiguous_body_handler,
            method="post",
            body_validator=FakeAgreementSchema,
        )


def test_api_route_rejects_missing_context():
    route = APIRouteDefinition(
        callback=no_context_handler,
        method=HTTPMethod.GET,
        name="missing-context",
        path="/orders/{order_id}",
        route_type=RouteType.API,
    )

    with pytest.raises(TypeError, match="must declare a 'ctx' or 'context' parameter"):
        APIHandlerArgumentsBuilder(route)


def test_api_route_validates_empty_body(api_route_dependencies, auth_headers, api_app_factory):
    client = api_app_factory(
        route_handler=default_body_handler,
        method="post",
        body_validator=OptionalAgreementSchema,
    )

    result = client.post("/auth/check", headers=auth_headers)

    assert result.status_code == HTTPStatus.OK
    assert result.json()["data"] == {"status": "Processing", "body": None}


def test_api_route_supports_async_handlers(
    api_route_dependencies, auth_headers, api_app_factory, async_ok_handler
):
    client = api_app_factory(route_handler=async_ok_handler)

    result = client.get("/auth/check", headers=auth_headers)

    assert result.status_code == HTTPStatus.OK
    assert result.json()["data"] == {"ok": True}


def test_api_route_rejects_invalid_response(api_route_dependencies, auth_headers, api_app_factory):
    client = api_app_factory(route_handler=invalid_response_handler)

    result = client.get("/auth/check", headers=auth_headers)

    assert result.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert result.json()["title"] == "Internal Server Error"


def test_api_route_maps_unhandled_errors(api_route_dependencies, auth_headers, api_app_factory):
    client = api_app_factory(route_handler=unhandled_error_handler)

    result = client.get("/auth/check", headers=auth_headers)

    assert result.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert result.json()["detail"] == (
        "An unexpected error occurred. Contact support with the correlation id below."
    )


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
        correlation_id="corr-1",
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
        "mpt_extension_sdk.api.builders.execution.record_exception", autospec=True
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
        "/adobe/orders?include_closed=YES&limit=25&tag=a&tag=b&malformed=not-a-bool&is_closed=off",
        headers=auth_headers,
    )

    assert result.status_code == HTTPStatus.OK
    assert result.json()["data"] == {
        "contains_limit": True,
        "first_tag": "b",
        "include_closed": True,
        "is_closed": False,
        "limit": 25,
        "missing_int": 15,
        "tags": ["a", "b"],
        "fallback": False,
        "malformed": True,
        "query": [
            ["include_closed", "YES"],
            ["limit", "25"],
            ["tag", "a"],
            ["tag", "b"],
            ["malformed", "not-a-bool"],
            ["is_closed", "off"],
        ],
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
    api_route_dependencies,
    api_app_factory,
    auth_claims_factory,
    forbidden_handler,
    jwt_token_factory,
):
    vendor_auth_token = jwt_token_factory(auth_claims_factory(account_type="Vendor"))
    client = api_app_factory(
        route_handler=forbidden_handler,
        method="post",
        prefix="/agreements",
        path="/{agreement_id}/sync",
        name="agreement-sync",
    )

    result = client.post(
        "/agreements/AGR-1/sync", headers={"Authorization": f"Bearer {vendor_auth_token}"}
    )

    assert result.status_code == HTTPStatus.FORBIDDEN
    assert result.json()["detail"] == "Only client accounts are supported"


def test_api_route_builds_context_from_auth(
    api_route_dependencies,
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


def test_api_route_rejects_expired_token(
    api_app_factory, auth_claims_factory, jwt_token_factory, ok_handler
):
    expired_auth_token = jwt_token_factory(auth_claims_factory(exp=EXPIRED_EXP_TIMESTAMP))
    client = api_app_factory(route_handler=ok_handler)

    result = client.get("/auth/check", headers={"Authorization": f"Bearer {expired_auth_token}"})

    assert result.status_code == HTTPStatus.UNAUTHORIZED
    assert result.json()["title"] == "Unauthorized"


def test_api_route_rejects_mismatched_ext_id(
    api_route_dependencies,
    api_app_factory,
    auth_claims_factory,
    jwt_token_factory,
    mock_api_service,
    ok_handler,
):
    mismatched_token = jwt_token_factory(auth_claims_factory(extension_id="EXT-2"))
    client = api_app_factory(route_handler=ok_handler)

    result = client.get("/auth/check", headers={"Authorization": f"Bearer {mismatched_token}"})

    assert result.status_code == HTTPStatus.UNAUTHORIZED
    assert result.json()["title"] == "Unauthorized"
    mock_api_service.service_type.from_auth_context.assert_not_awaited()


def test_api_route_rejects_empty_account_id(
    api_app_factory, auth_claims_factory, jwt_token_factory, ok_handler
):
    empty_account_token = jwt_token_factory(auth_claims_factory(account_id=""))
    client = api_app_factory(route_handler=ok_handler)

    result = client.get("/auth/check", headers={"Authorization": f"Bearer {empty_account_token}"})

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
    api_route_dependencies, auth_headers, api_app_factory, invalid_pagination_handler
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
