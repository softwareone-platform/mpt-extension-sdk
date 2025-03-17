import json
from functools import wraps

from requests import HTTPError, JSONDecodeError


class AirTableError(Exception):
    pass


class AirTableHttpError(AirTableError):
    def __init__(self, status_code: int, content: str):
        self.status_code = status_code
        self.content = content
        super().__init__(f"{self.status_code} - {self.content}")


class AirTableAPIError(AirTableHttpError):
    def __init__(self, status_code: int, payload) -> None:
        super().__init__(status_code, json.dumps(payload))
        self.payload = payload
        self.code = status_code
        self.message = payload.get("error", {}).get("message", "")

    def __str__(self) -> str:
        return f"{self.code} - {self.message}"

    def __repr__(self) -> str:
        return str(self.payload)


def wrap_airtable_http_error(func):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPError as e:
            try:
                raise AirTableAPIError(e.response.status_code, e.response.json())
            except JSONDecodeError:
                raise AirTableHttpError(
                    e.response.status_code, e.response.content.decode()
                )

    return _wrapper
