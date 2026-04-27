from mpt_extension_sdk.api.models.events import EventResponse
from mpt_extension_sdk.errors.mapping import map_exception_to_event_response
from mpt_extension_sdk.errors.pipeline import CancelError, DeferError, FailError
from mpt_extension_sdk.errors.runtime import ExtRuntimeError


def test_map_exc_to_event_response_cancel(mocker):
    mock_event_response = mocker.patch.object(EventResponse, "cancel", autospec=True)

    result = map_exception_to_event_response(CancelError())

    assert result == mock_event_response.return_value
    mock_event_response.assert_called_once_with(reason="Cancelled")


def test_map_exc_to_event_response_cancel_reason(mocker):
    mock_event_response = mocker.patch.object(EventResponse, "cancel", autospec=True)

    result = map_exception_to_event_response(CancelError("fake error msg"))

    assert result == mock_event_response.return_value
    mock_event_response.assert_called_once_with(reason="fake error msg")


def test_map_exc_to_event_response_defer(mocker):
    mock_event_response = mocker.patch.object(EventResponse, "reschedule", autospec=True)

    result = map_exception_to_event_response(DeferError("fake error msg", delay_seconds=30))

    assert result == mock_event_response.return_value
    mock_event_response.assert_called_once_with(seconds=30)


def test_map_exc_to_event_response_fail(mocker):
    mock_event_response = mocker.patch.object(EventResponse, "cancel", autospec=True)

    result = map_exception_to_event_response(FailError("Failed to process the event"))

    assert result == mock_event_response.return_value
    mock_event_response.assert_called_once_with(reason="Failed to process the event")


def test_map_exc_to_event_response_runtime_error(mocker):
    mock_event_response = mocker.patch.object(EventResponse, "cancel", autospec=True)

    result = map_exception_to_event_response(ExtRuntimeError("fake error msg"))

    assert result == mock_event_response.return_value
    mock_event_response.assert_called_once_with(reason="Runtime error")


def test_map_exc_to_event_response_unexpected(mocker):
    mock_event_response = mocker.patch.object(EventResponse, "cancel", autospec=True)

    result = map_exception_to_event_response(Exception())

    assert result == mock_event_response.return_value
    mock_event_response.assert_called_once_with(reason="Unexpected error")
