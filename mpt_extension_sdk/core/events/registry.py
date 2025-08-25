from collections.abc import Callable, MutableMapping, Sequence
from typing import Any

from mpt_extension_sdk.core.events.dataclasses import Event, EventType

EventListener = Callable[[Any, Event], None]


class EventsRegistry:
    """Registry for event listeners."""
    def __init__(
        self,
    ) -> None:
        self.listeners: MutableMapping[str, EventListener] = {}

    def listener(
        self,
        event_type: EventType,
        /,
    ) -> Callable[[EventListener], EventListener]:
        """
        Unique identifier of the event type.

        ## Example

        ```python
        from mpt_extension_sdk.core import Extension

        ext = Extension()


        @ext.events.listener("orders")
        def process_order(client, event):
            ...
        ```
        """

        def decorator(func: EventListener) -> EventListener:
            self.listeners[event_type] = func
            return func

        return decorator

    def get_listener(
        self,
        event_type: EventType,
    ) -> EventListener | None:
        """Get the listener for a specific event type."""
        return self.listeners.get(event_type)

    def get_registered_types(self) -> Sequence[str]:
        """Get a list of all registered event types."""
        return list(self.listeners.keys())

    def is_event_supported(
        self,
        event_type: EventType,
    ) -> bool:
        """Check if an event type is supported."""
        return event_type in self.listeners
