import json

import pytest
from fastapi import Request, Response

from mpt_extension_sdk.api.builders.errors import (
    APIErrorResponseBuilder,
    RequestRejectedError,
    WebhookErrorResponseBuilder,
)
from mpt_extension_sdk.runtime.logging import correlation_id_ctx
from mpt_extension_sdk.webhooks import WebhookError


@pytest.fixture
def request_to_sync():
    return Request({"type": "http", "method": "POST", "path": "/sync", "headers": []})


@pytest.fixture
def correlation_id():
    token = correlation_id_ctx.set("corr-1")
    yield "corr-1"
    correlation_id_ctx.reset(token)


def test_rejected_error_carries_response():
    response = Response(status_code=400)

    result = RequestRejectedError(response)

    assert result.response is response


def test_api_unauthorized_returns_problem(request_to_sync):
    result = APIErrorResponseBuilder().unauthorized(request_to_sync)

    assert (result.status_code, json.loads(result.body)) == (
        401,
        {
            "type": "about:blank",
            "status": 401,
            "title": "Unauthorized",
            "detail": "Unauthorized",
            "instance": "/sync",
        },
    )


def test_api_unexpected_carries_correlation_id(request_to_sync, correlation_id):
    result = APIErrorResponseBuilder().unexpected(request_to_sync)

    payload = json.loads(result.body)
    assert (result.status_code, payload["correlation_id"]) == (500, correlation_id)


def test_webhook_build_returns_error_object():
    result = WebhookErrorResponseBuilder.build(WebhookError("AWS001", "Invalid account type"))

    assert (result.status_code, json.loads(result.body)) == (
        500,
        {"id": "AWS001", "message": "Invalid account type"},
    )


def test_webhook_invalid_payload_is_bad_request():
    result = WebhookErrorResponseBuilder.invalid_payload("The webhook body is not valid JSON")

    assert (result.status_code, json.loads(result.body)) == (
        400,
        {"id": "EXT003", "message": "The webhook body is not valid JSON"},
    )


def test_webhook_unauthorized_returns_ext002(request_to_sync):
    result = WebhookErrorResponseBuilder().unauthorized(request_to_sync)

    payload = json.loads(result.body)
    assert (result.status_code, payload["id"]) == (401, "EXT002")


def test_webhook_unexpected_has_correlation_id(request_to_sync, correlation_id):
    result = WebhookErrorResponseBuilder().unexpected(request_to_sync)

    payload = json.loads(result.body)
    assert (result.status_code, payload["id"]) == (500, "EXT001")
    assert payload["message"].endswith(f"Correlation id: {correlation_id}")
