import uvicorn
from django.test import override_settings

from mpt_extension_sdk.runtime.workers import (
    start_event_consumer,
    start_uvicorn,
)


def test_start_uvicorn(mocker, mock_app_group_name):
    mocker.patch("mpt_extension_sdk.runtime.workers.initialize_extension", autospec=True)
    mock_run = mocker.patch.object(uvicorn, "run", autospec=True, return_value=None)

    start_uvicorn({}, group=mock_app_group_name)  # act

    mock_run.assert_called_once()


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    LOGGING={
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
            },
        },
        "root": {
            "handlers": ["console"],
        },
        "loggers": {
            "swo.mpt": {"handlers": ["console"]},
        },
    },
)
def test_start_event_consumer(mocker, monkeypatch):
    monkeypatch.setenv("MPT_INITIALIZE", "mpt_extension_sdk.runtime.workers.initialize")
    mock_call_command = mocker.patch(
        "mpt_extension_sdk.runtime.workers.call_command", autospec=True
    )
    dummy_ep = mocker.Mock(spec_set=["load"])
    dummy_ep.load.return_value = mocker.Mock(__module__="dummy", __name__="DummyConfig")
    mock_entry_points = mocker.patch("mpt_extension_sdk.runtime.utils.entry_points", autospec=True)
    mock_entry_points.return_value.select.return_value = [dummy_ep]

    start_event_consumer({})  # act

    mock_call_command.assert_called_once_with("consume_events")
