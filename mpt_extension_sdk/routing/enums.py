from enum import StrEnum


class RouteType(StrEnum):
    """Supported route families."""

    EVENT = "event"
    API = "api"
    SCHEDULE = "schedule"
    PLUG = "plug"


class EventDeliveryMode(StrEnum):
    """Supported event delivery modes."""

    EVENT = "event"
    TASK = "task"


class HTTPMethod(StrEnum):
    """Supported authenticated API methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
