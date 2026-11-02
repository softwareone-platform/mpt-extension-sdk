from http import HTTPStatus

from mpt_extension_sdk.webhooks.errors import (
    WebhookError,
    WebhookInvalidPayloadError,
    WebhookUnauthorizedError,
    WebhookUnexpectedError,
)


def test_webhook_error_defaults_to_server_error():
    result = WebhookError("AWS001", "Invalid account type")

    assert (result.error_id, result.message, result.status_code) == (
        "AWS001",
        "Invalid account type",
        HTTPStatus.INTERNAL_SERVER_ERROR,
    )


def test_webhook_error_takes_status_code():
    result = WebhookError("AWS010", "Provider unavailable", status_code=HTTPStatus.BAD_GATEWAY)

    assert result.status_code == HTTPStatus.BAD_GATEWAY


def test_invalid_payload_error_is_bad_request():
    result = WebhookInvalidPayloadError("The webhook body is not valid JSON")

    assert (result.error_id, result.message, result.status_code) == (
        "EXT003",
        "The webhook body is not valid JSON",
        HTTPStatus.BAD_REQUEST,
    )


def test_unauthorized_error_is_unauthorized():
    result = WebhookUnauthorizedError()

    assert (result.error_id, result.message, result.status_code) == (
        "EXT002",
        "The webhook call could not be authenticated",
        HTTPStatus.UNAUTHORIZED,
    )


def test_unexpected_error_has_correlation_id():
    result = WebhookUnexpectedError("corr-1")

    assert (result.error_id, result.message, result.status_code) == (
        "EXT001",
        "Unexpected webhook error - contact support. Correlation id: corr-1",
        HTTPStatus.INTERNAL_SERVER_ERROR,
    )
