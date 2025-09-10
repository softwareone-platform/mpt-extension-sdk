from logging.config import DictConfigurator

from django.core.wsgi import get_wsgi_application
from django.test import override_settings

from mpt_extension_sdk.runtime.workers import (
    ExtensionWebApplication,
    start_event_consumer,
    start_gunicorn,
)


def test_extension_web_application(mock_gunicorn_logging_config):
    gunicorn_options = {
        "bind": "localhost:8080",
        "logconfig_dict": mock_gunicorn_logging_config,
    }
    wsgi_app = get_wsgi_application()
    ext_web_app = ExtensionWebApplication(wsgi_app, gunicorn_options)
    assert ext_web_app.application == wsgi_app
    assert ext_web_app.options == gunicorn_options


def test_extension_web_application_load_config(mock_gunicorn_logging_config):
    gunicorn_options = {
        "bind": "localhost:8080",
        "logconfig_dict": mock_gunicorn_logging_config,
    }
    wsgi_app = get_wsgi_application()
    ext_web_app = ExtensionWebApplication(wsgi_app, gunicorn_options)
    ext_web_app.load_config()
    assert ext_web_app.application == wsgi_app
    assert ext_web_app.options == gunicorn_options


@override_settings(
    MPT_PRODUCTS_IDS="PRD-1111-1111",
    LOGGING={
        "version": 1,
        "root": {
            "handlers": ["rich"],
        },
        "loggers": {
            "mpt_extension_sdk": {},
            "swo.mpt": {},
        },
    },
)
def test_start_gunicorn(mocker, monkeypatch, mock_app_group_name):
    monkeypatch.setenv("MPT_INITIALIZE", "mpt_extension_sdk.runtime.workers.initialize")

    mocker.patch.object(
        DictConfigurator,
        "configure",
        return_value=None,
    )
    mock_run = mocker.patch.object(
        ExtensionWebApplication,
        "run",
        return_value=None,
    )

    start_gunicorn({}, group=mock_app_group_name)
    mock_run.assert_called_once()


def test_start_event_consumer(mocker, monkeypatch, settings):
    """Test that start_event_consumer calls initialize_func and then call_command."""
    settings.MPT_PRODUCTS_IDS = "PRD-1111-1111"

    monkeypatch.setenv("MPT_INITIALIZE", "mpt_extension_sdk.runtime.workers.initialize")

    mock_call_command = mocker.patch("mpt_extension_sdk.runtime.workers.call_command")

    dummy_ep = mocker.Mock(autospec=True)
    dummy_ep.load.return_value = mocker.Mock(__module__="dummy", __name__="DummyConfig")
    mock_entry_points = mocker.patch("mpt_extension_sdk.runtime.utils.entry_points")
    mock_entry_points.return_value.select.return_value = [dummy_ep]

    if not hasattr(settings, "LOGGING"):
        settings.LOGGING = {}
    if "loggers" not in settings.LOGGING:
        settings.LOGGING["loggers"] = {}
    settings.LOGGING["loggers"]["swo.mpt"] = {"handlers": ["console"]}

    start_event_consumer({})

    mock_call_command.assert_called_once_with("consume_events")
