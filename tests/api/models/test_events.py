import pytest

from mpt_extension_sdk.api.models.events import (
    EventObject,
    EventObjectType,
    EventResponse,
    ResponseEnum,
)


def test_event_response_cancel():
    result = EventResponse.cancel(reason="Fake reason")

    assert result.response == ResponseEnum.CANCEL
    assert result.cancel_reason == "Fake reason"


def test_event_response_ok():
    result = EventResponse.ok()

    assert result.response == ResponseEnum.OK


def test_event_response_reschedule():
    result = EventResponse.reschedule(seconds=0)

    assert result.response == ResponseEnum.DEFER
    assert result.defer_delay == 0


def test_event_response_reschedule_to_dict():
    result = EventResponse.reschedule(seconds=120)

    assert result.to_dict() == {"response": "Delay", "delay": 120}


@pytest.mark.parametrize(
    ("object_type", "expected_type"),
    [("Order", EventObjectType.ORDER), ("Agreement", EventObjectType.AGREEMENT)],
)
def test_event_object_parses_known_type(object_type, expected_type):
    result = EventObject.model_validate({"id": "OBJ-1", "objectType": object_type, "name": "Obj"})

    assert result.object_type is expected_type


def test_event_object_keeps_unknown_type():
    result = EventObject.model_validate({"id": "AST-1", "objectType": "Asset", "name": "Asset"})

    assert result.object_type == "Asset"
