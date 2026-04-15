from mpt_extension_sdk.api.models.events import EventResponse, ResponseEnum


def test_event_response_reschedule_accepts_zero():
    result = EventResponse.reschedule(seconds=0)

    assert result.response == ResponseEnum.DEFER
    assert result.defer_delay == "PT0S"
