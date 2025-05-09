from logging.config import DictConfigurator

from django.core.wsgi import get_wsgi_application
from django.test import override_settings

from mpt_extension_sdk.runtime.workers import (
    ExtensionWebApplication,
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
def test_start_gunicorn(mocker):
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
    start_gunicorn({})
    mock_run.assert_called_once()
