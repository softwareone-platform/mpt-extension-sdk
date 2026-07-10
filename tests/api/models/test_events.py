from mpt_extension_sdk.api.models.events import EventResponse, ResponseEnum


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
