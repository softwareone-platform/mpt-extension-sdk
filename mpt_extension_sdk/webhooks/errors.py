from http import HTTPStatus


class WebhookError(Exception):
    """Raised by a webhook handler that cannot produce an answer."""

    def __init__(
        self,
        error_id: str,
        message: str,
        *,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
    ) -> None:
        self.error_id = error_id
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class WebhookInvalidPayloadError(WebhookError):
    """Answers a webhook call whose body the SDK cannot read as its webhook type."""

    def __init__(self, message: str) -> None:
        super().__init__("EXT003", message, status_code=HTTPStatus.BAD_REQUEST)


class WebhookUnauthorizedError(WebhookError):
    """Answers a webhook call that could not be authenticated."""

    def __init__(self) -> None:
        super().__init__(
            "EXT002",
            "The webhook call could not be authenticated",
            status_code=HTTPStatus.UNAUTHORIZED,
        )


class WebhookUnexpectedError(WebhookError):
    """Answers a webhook call whose handler failed with an unexpected error."""

    def __init__(self, correlation_id: str | None) -> None:
        super().__init__(
            "EXT001",
            f"Unexpected webhook error - contact support. Correlation id: {correlation_id}",
        )
