import pytest

from mpt_extension_sdk.core.events.registry import EventsRegistry
from mpt_extension_sdk.runtime.utils import get_events_registry


@pytest.fixture
def events_registry():
    registry = EventsRegistry()

    @registry.listener("orders")
    def test_listener(client, event):
        pass

    return registry


def test_get_events_registry(mock_app_group_name):
    result = get_events_registry(group=mock_app_group_name)

    assert isinstance(result, EventsRegistry)


def test_registry_get_listener(events_registry):
    result = events_registry.get_listener("orders")

    assert result.__name__ == "test_listener"


def test_registry_get_registered_types(events_registry):
    result = events_registry.get_registered_types()

    assert result == ["orders"]


@pytest.mark.parametrize(("event", "expected_result"), [("orders", True), ("unknown", False)])
def test_registry_is_event_supported(event, expected_result, events_registry):
    result = events_registry.is_event_supported(event)

    assert result is expected_result
