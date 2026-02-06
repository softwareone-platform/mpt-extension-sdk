import importlib


def test_dynamic_trace_span(mocker):
    mocker_tracer_instance = mocker.MagicMock(spec=["start_as_current_span", "start_span"])
    mock_span_cm = mocker.MagicMock(spec=["__enter__", "__exit__"])
    mock_span = mocker.MagicMock(spec=["__enter__", "__exit__", "set_attribute", "end"])
    mock_span_cm.__enter__.return_value = mock_span
    mocker_tracer_instance.start_as_current_span.return_value = mock_span_cm
    mocker.patch(
        "mpt_extension_sdk.runtime.tracer.trace.get_tracer",
        autospec=True,
        return_value=mocker_tracer_instance,
    )
    from mpt_extension_sdk.runtime import tracer  # noqa: PLC0415

    # BL
    importlib.reload(tracer)

    # BL
    def name_fn(x):
        return f"result-{x}"

    # BL
    @tracer.dynamic_trace_span(name_fn)
    def test_func(x):
        return x + 1

    result = test_func(5)

    assert result == 6
    mocker_tracer_instance.start_as_current_span.assert_called_once_with("result-5")
    mock_span_cm.__enter__.assert_called_once()
