from ninja import NinjaAPI

from mpt_extension_sdk.core.events.registry import EventsRegistry


class Extension:
    """Base class for all extensions."""
    def __init__(
        self,
        /,
    ) -> None:
        self.events: EventsRegistry = EventsRegistry()
        self.api: NinjaAPI = NinjaAPI()
