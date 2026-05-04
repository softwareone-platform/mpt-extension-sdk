"""FastAPI route builders for SDK route definitions."""

from mpt_extension_sdk.api.builders.api import create_api_route
from mpt_extension_sdk.api.builders.event import create_event_route

__all__ = [  # noqa: WPS410
    "create_api_route",
    "create_event_route",
]
