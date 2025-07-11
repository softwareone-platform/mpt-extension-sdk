from mpt_extension_sdk.core.events.registry import EventsRegistry
from mpt_extension_sdk.runtime.utils import get_events_registry


def test_get_events_registry(mock_app_group_name):
    registry = get_events_registry(group=mock_app_group_name)
    assert isinstance(registry, EventsRegistry)


def test_registry_get_listener():
    registry = EventsRegistry()

    @registry.listener("orders")
    def test_listener(client, event):
        pass

    assert registry.get_listener("orders") == test_listener


def test_registry_get_registered_types():
    registry = EventsRegistry()

    @registry.listener("orders")
    def test_listener(client, event):
        pass

    assert registry.get_registered_types() == ["orders"]


def test_registry_is_event_supported():
    registry = EventsRegistry()

    @registry.listener("orders")
    def test_listener(client, event):
        pass

    assert registry.is_event_supported("orders")


def test_registry_is_event_not_supported():
    registry = EventsRegistry()

    @registry.listener("orders")
    def test_listener(client, event):
        pass

    assert not registry.is_event_supported("unknown")
