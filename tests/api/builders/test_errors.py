import json

import pytest
from fastapi import Request, Response

from mpt_extension_sdk.api.builders.errors import (
    APIErrorResponseBuilder,
    RequestRejectedError,
)
from mpt_extension_sdk.runtime.logging import correlation_id_ctx


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
