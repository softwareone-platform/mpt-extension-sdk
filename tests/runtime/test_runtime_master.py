from django.test import override_settings

from mpt_extension_sdk.runtime.master import Master


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    LOGGING={"loggers": {"mpt_extension_sdk": {}, "swo.mpt": {}}},
)
def test_master_start_signals_handler_all(runtime_master_options_factory):
    mock_runtime_master_options = runtime_master_options_factory(component="all")
    mock_runtime_master = Master(mock_runtime_master_options)
    mock_runtime_master.setup_signals_handler()
    mock_runtime_master.start()
    is_started = mock_runtime_master.monitor_thread.is_alive()
    mock_runtime_master.stop()
    assert is_started


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    LOGGING={"loggers": {"mpt_extension_sdk": {}, "swo.mpt": {}}},
)
def test_master_start_signals_handler_api(runtime_master_options_factory):
    mock_runtime_master_options = runtime_master_options_factory(component="api")
    mock_runtime_master = Master(mock_runtime_master_options)
    mock_runtime_master.setup_signals_handler()
    mock_runtime_master.start()
    is_started = mock_runtime_master.monitor_thread.is_alive()
    mock_runtime_master.stop()
    assert is_started


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    LOGGING={"loggers": {"mpt_extension_sdk": {}, "swo.mpt": {}}},
)
def test_master_start_signals_handler_consumer(runtime_master_options_factory):
    mock_runtime_master_options = runtime_master_options_factory(component="consumer")
    mock_runtime_master = Master(mock_runtime_master_options)
    mock_runtime_master.setup_signals_handler()
    mock_runtime_master.start()
    is_started = mock_runtime_master.monitor_thread.is_alive()
    mock_runtime_master.stop()
    assert is_started


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    LOGGING={"loggers": {"mpt_extension_sdk": {}, "swo.mpt": {}}},
)
def test_master_start_signals_handler_other(runtime_master_options_factory):
    mock_runtime_master_options = runtime_master_options_factory(component="other")
    mock_runtime_master = Master(mock_runtime_master_options)
    mock_runtime_master.setup_signals_handler()
    mock_runtime_master.start()
    is_started = mock_runtime_master.monitor_thread.is_alive()
    mock_runtime_master.stop()
    assert is_started


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    LOGGING={"loggers": {"mpt_extension_sdk": {}, "swo.mpt": {}}},
)
def test_master_restart_signals_handler(runtime_master_options_factory):
    mock_runtime_master_options = runtime_master_options_factory(component="all")
    mock_runtime_master = Master(mock_runtime_master_options)
    mock_runtime_master.setup_signals_handler()
    mock_runtime_master.start()
    mock_runtime_master.restart()
    is_restarted = mock_runtime_master.monitor_thread.is_alive()
    mock_runtime_master.stop()
    assert is_restarted


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    LOGGING={"loggers": {"mpt_extension_sdk": {}, "swo.mpt": {}}},
)
def test_master_stop_signals_handler(runtime_master_options_factory):
    mock_runtime_master_options = runtime_master_options_factory(component="all")
    mock_runtime_master = Master(mock_runtime_master_options)
    mock_runtime_master.setup_signals_handler()
    mock_runtime_master.start()
    mock_runtime_master.restart()
    mock_runtime_master.stop()
    is_stopped = not mock_runtime_master.monitor_thread.is_alive()
    assert is_stopped
