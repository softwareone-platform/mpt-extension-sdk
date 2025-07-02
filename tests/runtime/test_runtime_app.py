from click.testing import CliRunner

import mpt_extension_sdk.runtime.djapp.conf.default as default_settings
from mpt_extension_sdk.runtime.commands.run import run
from mpt_extension_sdk.runtime.master import Master


def test_run(
    mocker
):
    component = "all"

    mock_master_run = mocker.patch.object(Master, "run", return_value=None)

    runner = CliRunner()
    result = runner.invoke(run, [
        component,
        "--color"
    ])
    assert result.exit_code == 0
    assert mock_master_run.call_count == 1


def test_run_with_debug_py(
    mocker
):
    component = "all"

    debug_py = "localhost:5678"

    mock_master_run = mocker.patch.object(Master, "run", return_value=None)

    mock_debugpy = mocker.patch(
        "mpt_extension_sdk.runtime.commands.run.debugpy.listen",
        return_value=None
    )

    runner = CliRunner()
    result = runner.invoke(run, [
        component,
        "--debug-py",
        debug_py,
    ])
    assert result.exit_code == 0
    assert mock_master_run.call_count == 1
    assert mock_debugpy.call_count == 1


def test_default():
    assert default_settings.ALLOWED_HOSTS is not None
    assert default_settings.SECRET_KEY is not None
    assert "mpt_extension_sdk.runtime.djapp.apps.DjAppConfig" in default_settings.INSTALLED_APPS
    assert (
        "mpt_extension_sdk.runtime.djapp.middleware.MPTClientMiddleware"
    ) in default_settings.MIDDLEWARE
    assert default_settings.ROOT_URLCONF == "mpt_extension_sdk.runtime.djapp.conf.urls"
    assert default_settings.EXTENSION_CONFIG is not None
    assert default_settings.MPT_API_BASE_URL is not None
    assert default_settings.MPT_PRODUCTS_IDS is not None
    assert default_settings.MPT_API_TOKEN is not None
    assert default_settings.MPT_API_TOKEN_OPERATIONS is not None
    assert default_settings.MPT_PORTAL_BASE_URL is not None


def test_urls(
    monkeypatch,
    mock_app_group_name,
):
    import mpt_extension_sdk.constants as constants
    monkeypatch.setattr(constants, "DEFAULT_APP_CONFIG_GROUP", mock_app_group_name)
    import mpt_extension_sdk.runtime.djapp.conf.urls as urls
    assert urls.urlpatterns is not None
    assert len(urls.urlpatterns) == 2
