import pytest

from mpt_extension_sdk.api.models.events import EventResponse
from mpt_extension_sdk.errors.mapping import map_exception_to_event_response
from mpt_extension_sdk.errors.pipeline import CancelError, DeferError, FailError
from mpt_extension_sdk.errors.runtime import ExtRuntimeError


@pytest.mark.parametrize(
    ("error", "expected_reason"),
    [
        (CancelError(), "Cancelled"),
        (CancelError("fake error msg"), "fake error msg"),
        (FailError(), "Failed to process the event"),
        (FailError("fake error msg"), "fake error msg"),
        (ExtRuntimeError(), "Runtime error"),
        (ExtRuntimeError("fake internal detail"), "Runtime error"),
        (Exception(), "Unexpected error: Exception"),
        (KeyError("fake internal detail"), "Unexpected error: KeyError"),
    ],
)
def test_map_exc_to_event_response_cancel(mocker, error, expected_reason):
    mock_event_response = mocker.patch.object(EventResponse, "cancel", autospec=True)

    result = map_exception_to_event_response(error)

    assert result == mock_event_response.return_value
    mock_event_response.assert_called_once_with(reason=expected_reason)


def test_map_exc_to_event_response_defer(mocker):
    mock_event_response = mocker.patch.object(EventResponse, "reschedule", autospec=True)

    result = map_exception_to_event_response(DeferError("fake error msg", delay_seconds=30))

    assert result == mock_event_response.return_value
    mock_event_response.assert_called_once_with(seconds=30)
