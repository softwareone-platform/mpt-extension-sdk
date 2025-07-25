from unittest.mock import MagicMock

from django.test import override_settings

from mpt_extension_sdk.runtime.initializer import initialize
from mpt_extension_sdk.runtime.master import (
    Master,
    start_event_consumer_worker,
    start_gunicorn_worker,
)


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    LOGGING={"loggers": {"mpt_extension_sdk": {}, "swo.mpt": {}}},
)
def test_master_start_signals_handler_all(
    mocker, runtime_master_options_factory, settings, mock_process_id
):
    """
    Test master start with signals handler for all components
    """

    mock_start_process = mocker.patch("mpt_extension_sdk.runtime.master.start_process")

    mock_process = MagicMock(autospec=True)
    mock_process.pid = mock_process_id
    mock_start_process.return_value = mock_process

    mock_runtime_master_options = runtime_master_options_factory(component="all")
    mock_runtime_master = Master(
        mock_runtime_master_options, settings=settings, initialize_func=initialize
    )
    mock_runtime_master.setup_signals_handler()
    mock_runtime_master.start()
    is_started = mock_runtime_master.monitor_thread.is_alive()
    mock_runtime_master.stop()
    assert is_started


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    LOGGING={"loggers": {"mpt_extension_sdk": {}, "swo.mpt": {}}},
)
def test_master_start_signals_handler_api(
    mocker, runtime_master_options_factory, settings, mock_process_id
):
    """
    Test master start with signals handler for API component
    """

    mock_start_process = mocker.patch("mpt_extension_sdk.runtime.master.start_process")

    mock_process = MagicMock(autospec=True)
    mock_process.pid = mock_process_id
    mock_start_process.return_value = mock_process

    mock_runtime_master_options = runtime_master_options_factory(component="api")
    mock_runtime_master = Master(
        mock_runtime_master_options, settings=settings, initialize_func=initialize
    )
    mock_runtime_master.setup_signals_handler()
    mock_runtime_master.start()
    is_started = mock_runtime_master.monitor_thread.is_alive()
    mock_runtime_master.stop()
    assert is_started


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    LOGGING={"loggers": {"mpt_extension_sdk": {}, "swo.mpt": {}}},
)
def test_master_start_signals_handler_consumer(
    mocker, runtime_master_options_factory, settings, mock_process_id
):
    """
    Test master start with signals handler for consumer component
    """
    mock_start_process = mocker.patch("mpt_extension_sdk.runtime.master.start_process")

    mock_process = MagicMock(autospec=True)
    mock_process.pid = mock_process_id
    mock_start_process.return_value = mock_process

    mock_runtime_master_options = runtime_master_options_factory(component="consumer")
    mock_runtime_master = Master(
        mock_runtime_master_options, settings=settings, initialize_func=initialize
    )
    mock_runtime_master.setup_signals_handler()
    mock_runtime_master.start()
    is_started = mock_runtime_master.monitor_thread.is_alive()
    mock_runtime_master.stop()
    assert is_started


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    LOGGING={"loggers": {"mpt_extension_sdk": {}, "swo.mpt": {}}},
)
def test_master_start_signals_handler_other(
    mocker, runtime_master_options_factory, settings, mock_process_id
):
    """
    Test master start with signals handler for other components
    """
    mock_start_process = mocker.patch("mpt_extension_sdk.runtime.master.start_process")

    mock_process = MagicMock(autospec=True)
    mock_process.pid = mock_process_id
    mock_start_process.return_value = mock_process

    mock_runtime_master_options = runtime_master_options_factory(component="other")
    mock_runtime_master = Master(
        mock_runtime_master_options, settings=settings, initialize_func=initialize
    )
    mock_runtime_master.setup_signals_handler()
    mock_runtime_master.start()
    is_started = mock_runtime_master.monitor_thread.is_alive()
    mock_runtime_master.stop()
    assert is_started


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    LOGGING={"loggers": {"mpt_extension_sdk": {}, "swo.mpt": {}}},
)
def test_master_restart_signals_handler(
    mocker, runtime_master_options_factory, settings, mock_process_id
):
    """
    Test master restart with signals handler
    """
    mock_start_process = mocker.patch("mpt_extension_sdk.runtime.master.start_process")

    mock_process = MagicMock(autospec=True)
    mock_process.pid = mock_process_id
    mock_start_process.return_value = mock_process

    mock_runtime_master_options = runtime_master_options_factory(component="all")
    mock_runtime_master = Master(
        mock_runtime_master_options, settings=settings, initialize_func=initialize
    )
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
def test_master_stop_signals_handler(
    mocker, runtime_master_options_factory, settings, mock_process_id
):
    """
    Test master stop with signals handler
    """
    mock_start_process = mocker.patch("mpt_extension_sdk.runtime.master.start_process")

    mock_process = MagicMock(autospec=True)
    mock_process.pid = mock_process_id
    mock_start_process.return_value = mock_process

    mock_runtime_master_options = runtime_master_options_factory(component="all")
    mock_runtime_master = Master(
        mock_runtime_master_options, settings=settings, initialize_func=initialize
    )
    mock_runtime_master.setup_signals_handler()
    mock_runtime_master.start()
    mock_runtime_master.restart()
    mock_runtime_master.stop()
    is_stopped = not mock_runtime_master.monitor_thread.is_alive()
    assert is_stopped


def test_start_event_consumer_worker(mocker, mock_gunicorn_options):
    """
    Test start_event_consumer_worker calls start_event_consumer correctly
    """
    initialize_func = initialize

    mock_start_event_consumer = mocker.patch(
        "mpt_extension_sdk.runtime.master.start_event_consumer"
    )

    start_event_consumer_worker(mock_gunicorn_options, initialize_func)

    mock_start_event_consumer.assert_called_once_with(
        initialize_func, mock_gunicorn_options
    )


def test_start_gunicorn_worker(mocker, mock_gunicorn_options):
    """
    Test start_gunicorn_worker calls start_gunicorn correctly
    """
    initialize_func = initialize

    mock_start_gunicorn = mocker.patch(
        "mpt_extension_sdk.runtime.master.start_gunicorn"
    )

    start_gunicorn_worker(mock_gunicorn_options, initialize_func)

    mock_start_gunicorn.assert_called_once_with(initialize_func, mock_gunicorn_options)
