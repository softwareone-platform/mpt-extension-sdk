import pytest
from watchfiles.run import CombinedProcess

from mpt_extension_sdk.runtime.master import Master


@pytest.fixture(autouse=True)
def mock_time_sleep(mocker):
    mocker.patch("mpt_extension_sdk.runtime.master.time.sleep", autospec=True)


@pytest.fixture
def mock_start_process(mocker):
    mock_process = mocker.Mock(pid="12345", spec=CombinedProcess)
    return mocker.patch(
        "mpt_extension_sdk.runtime.master.start_process", return_value=mock_process, autospec=True
    )


@pytest.fixture(autouse=True)
def override_default_settings(settings):
    settings.MPT_PRODUCTS_IDS = ("PRD-1111-1111",)
    settings.LOGGING = ({"loggers": {"mpt_extension_sdk": {}, "swo.mpt": {}}},)


@pytest.mark.parametrize("component", ["all", "api", "consumer", "other"])
def test_master_start_signals_handler(
    component, runtime_master_options_factory, settings, mock_start_process
):

    mock_runtime_master_options = runtime_master_options_factory(component=component)
    mock_runtime_master = Master(mock_runtime_master_options, settings=settings)
    mock_runtime_master.setup_signals_handler()
    mock_runtime_master.start()

    result = mock_runtime_master.monitor_thread.is_alive()

    assert result is True
    mock_start_process.assert_called()
    mock_runtime_master.stop()


def test_master_restart_signals_handler(
    runtime_master_options_factory, settings, mock_start_process
):
    mock_runtime_master_options = runtime_master_options_factory(component="all")
    mock_runtime_master = Master(mock_runtime_master_options, settings=settings)
    mock_runtime_master.setup_signals_handler()
    mock_runtime_master.start()
    mock_runtime_master.restart()

    result = mock_runtime_master.monitor_thread.is_alive()

    assert result is True
    mock_start_process.assert_called()
    mock_runtime_master.stop()


def test_master_stop_signals_handler(runtime_master_options_factory, settings, mock_start_process):
    mock_runtime_master_options = runtime_master_options_factory(component="all")
    mock_runtime_master = Master(mock_runtime_master_options, settings=settings)
    mock_runtime_master.setup_signals_handler()
    mock_runtime_master.start()
    mock_runtime_master.restart()
    mock_runtime_master.stop()

    result = mock_runtime_master.monitor_thread.is_alive()

    assert result is False
    mock_start_process.assert_called()
