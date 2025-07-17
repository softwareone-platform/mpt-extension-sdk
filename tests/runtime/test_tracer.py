import importlib
from unittest.mock import MagicMock


def test_dynamic_trace_span(mocker):
    mocker_tracer_instance = MagicMock()
    mock_span_cm = MagicMock(spec=["__enter__", "__exit__"])
    mock_span = MagicMock()
    mock_span_cm.__enter__.return_value = mock_span
    mocker_tracer_instance.start_as_current_span.return_value = mock_span_cm

    mocker.patch(
        "mpt_extension_sdk.runtime.tracer.trace.get_tracer",
        autospec=True,
        return_value=mocker_tracer_instance
    )

    import mpt_extension_sdk.runtime.tracer as tracer
    importlib.reload(tracer)

    def name_fn(x):
        return f"result-{x}"

    @tracer.dynamic_trace_span(name_fn)
    def test_func(x):
        return x + 1

    result = test_func(5)
    assert result == 6
    mocker_tracer_instance.start_as_current_span.assert_called_once_with("result-5")
    mock_span_cm.__enter__.assert_called_once()
