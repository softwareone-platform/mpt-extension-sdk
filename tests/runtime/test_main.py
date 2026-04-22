import importlib
import sys


def test_runtime_main_builds_app_from_settings(mocker, runtime_settings):
    expected_app = object()
    create_runtime_app = mocker.patch(
        "mpt_extension_sdk.runtime.app.create_runtime_app",
        autospec=True,
        return_value=expected_app,
    )
    get_runtime_settings = mocker.patch(
        "mpt_extension_sdk.settings.runtime.get_runtime_settings",
        autospec=True,
        return_value=runtime_settings,
    )
    sys.modules.pop("mpt_extension_sdk.runtime.main", None)

    result = importlib.import_module("mpt_extension_sdk.runtime.main")

    assert result.app is expected_app
    get_runtime_settings.assert_called_once_with()
    create_runtime_app.assert_called_once_with(runtime_settings=runtime_settings)
