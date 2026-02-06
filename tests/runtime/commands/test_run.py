from click.testing import CliRunner

import mpt_extension_sdk.runtime.djapp.conf.default as default_settings
from mpt_extension_sdk import constants
from mpt_extension_sdk.runtime.commands.run import run
from mpt_extension_sdk.runtime.master import Master


def test_run(mocker):
    mock_master_run = mocker.patch.object(Master, "run", autospec=True, return_value=None)
    mocker.patch(
        "mpt_extension_sdk.runtime.utils.get_initializer_function",
        autospec=True,
        return_value=mocker.Mock(spec=callable),
    )
    runner = CliRunner()

    result = runner.invoke(run, ["all", "--color"])

    assert result.exit_code == 0
    mock_master_run.assert_called_once()


def test_run_with_debug_py(mocker):
    debug_py = "localhost:5678"
    mock_master_run = mocker.patch.object(Master, "run", autospec=True, return_value=None)
    mocker.patch(
        "mpt_extension_sdk.runtime.utils.get_initializer_function",
        autospec=True,
        return_value=mocker.Mock(spec=callable),
    )
    mock_debugpy = mocker.patch(
        "mpt_extension_sdk.runtime.commands.run.debugpy.listen",
        autospec=True,
        return_value=None,
    )
    runner = CliRunner()

    result = runner.invoke(run, ["all", "--debug-py", debug_py])

    assert result.exit_code == 0
    mock_master_run.assert_called_once()
    mock_debugpy.assert_called_once()


def test_default():
    result = default_settings

    assert result.ALLOWED_HOSTS is not None
    assert result.SECRET_KEY is not None
    assert "mpt_extension_sdk.runtime.djapp.apps.DjAppConfig" in result.INSTALLED_APPS
    assert "mpt_extension_sdk.runtime.djapp.middleware.MPTClientMiddleware" in result.MIDDLEWARE
    assert result.ROOT_URLCONF == "mpt_extension_sdk.runtime.djapp.conf.urls"
    assert result.EXTENSION_CONFIG is not None
    assert result.MPT_API_BASE_URL is not None
    assert result.MPT_PRODUCTS_IDS is not None
    assert result.MPT_API_TOKEN is not None
    assert result.MPT_API_TOKEN_OPERATIONS is not None
    assert result.MPT_PORTAL_BASE_URL is not None
    assert result.MPT_KEY_VAULT_NAME is not None
    assert result.MPT_ORDERS_API_POLLING_INTERVAL_SECS is not None
    assert result.MPT_SETUP_CONTEXTS_FUNC is not None


def test_urls(monkeypatch, mock_app_group_name):
    monkeypatch.setattr(constants, "DEFAULT_APP_CONFIG_GROUP", mock_app_group_name)
    from mpt_extension_sdk.runtime.djapp.conf import urls  # noqa: PLC0415

    result = urls.urlpatterns

    assert result is not None
    assert len(result) == 2
