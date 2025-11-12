import json
from functools import wraps

from requests import HTTPError, JSONDecodeError
from requests.exceptions import RetryError


class MPTError(Exception):
    """Represents a generic MPT error."""


class MPTMaxRetryError(MPTError):
    """Represents a maximum request retry error."""


class MPTHttpError(MPTError):
    """Represents an HTTP error."""

    def __init__(self, status_code: int, content: str):
        self.status_code = status_code
        self.content = content
        super().__init__(f"{self.status_code} - {self.content}")


class MPTAPIError(MPTHttpError):
    """Represents an API error."""

    def __init__(self, status_code, payload):
        super().__init__(status_code, json.dumps(payload))
        self.payload = payload
        self.status = payload.get("status")
        self.title = payload.get("title")
        self.detail = payload.get("detail")
        self.trace_id = payload.get("traceId")
        self.errors = payload.get("errors")

    def __str__(self):
        base = f"{self.status} {self.title} - {self.detail} ({self.trace_id})"

        if self.errors:
            return f"{base}\n{json.dumps(self.errors, indent=2)}"
        return base

    def __repr__(self):
        return str(self.payload)


def transform_http_error(err):
    """Transform an HTTP error to an MPT error."""
    try:
        payload = err.response.json()
    except JSONDecodeError:
        return MPTHttpError(err.response.status_code, err.response.content.decode())
    return MPTAPIError(err.response.status_code, payload)


def wrap_mpt_http_error(func):
    """Wrap a function to catch MPT HTTP errors."""

    @wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPError as err:
            raise transform_http_error(err) from err
        except RetryError as retry_error:
            raise MPTMaxRetryError(str(retry_error))

    return _wrapper


class ValidationError:
    """Represents a validation error."""

    def __init__(self, err_id, message):
        self.id = err_id
        self.message = message

    def to_dict(self, **kwargs):
        """Convert the validation error to a dictionary."""
        return {
            "id": self.id,
            "message": self.message.format(**kwargs),
        }


ERR_EXT_UNHANDLED_EXCEPTION = ValidationError(
    "EXT001",
    "Order can't be processed. Failure reason: {error}",
)
