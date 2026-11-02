import json
from http import HTTPStatus

from mpt_extension_sdk.models.parameter import ParameterValue
from mpt_extension_sdk.webhooks import WebhookResponse


def test_ok_response_has_no_envelope():
    result = WebhookResponse.ok({"id": "ORD-1", "status": "Draft"}).to_http_response()

    assert (result.status_code, json.loads(result.body)) == (
        HTTPStatus.OK,
        {"id": "ORD-1", "status": "Draft"},
    )


def test_ok_response_leaves_out_unset_fields():
    parameter = ParameterValue.model_validate({"id": "PAR-1", "externalId": "accountType"})

    result = WebhookResponse.ok(parameter).to_http_response()

    assert json.loads(result.body) == {"id": "PAR-1", "externalId": "accountType"}


def test_error_response_defaults_to_server_error():
    result = WebhookResponse.error("AWS001", "Invalid account type").to_http_response()

    assert (result.status_code, json.loads(result.body)) == (
        HTTPStatus.INTERNAL_SERVER_ERROR,
        {"id": "AWS001", "message": "Invalid account type"},
    )


def test_error_response_takes_status_code():
    result = WebhookResponse.error(
        "AWS010", "Provider unavailable", status_code=HTTPStatus.BAD_GATEWAY
    ).to_http_response()

    assert result.status_code == HTTPStatus.BAD_GATEWAY
