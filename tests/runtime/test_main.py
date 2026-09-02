import importlib
import sys
from collections.abc import Callable
from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from mpt_extension_sdk.settings.runtime import RuntimeSettings


@pytest.fixture
def main_patches(mocker) -> Callable[[RuntimeSettings], MagicMock]:
    def factory(runtime_settings: RuntimeSettings) -> MagicMock:
        mocker.patch("mpt_extension_sdk.runtime.app.create_runtime_app", autospec=True)
        mocker.patch("mpt_extension_sdk.runtime.runner.create_meta_file", autospec=True)
        mocker.patch(
            "mpt_extension_sdk.settings.runtime.get_runtime_settings",
            autospec=True,
            return_value=runtime_settings,
        )
        register = mocker.patch(
            "mpt_extension_sdk.runtime.bootstrap.registration.register_instance_on_reload",
            autospec=True,
        )
        sys.modules.pop("mpt_extension_sdk.runtime.main", None)
        return register

    return factory


def test_runtime_main_builds_app_from_settings(mocker, runtime_settings):
    expected_app = object()
    create_runtime_app = mocker.patch(
        "mpt_extension_sdk.runtime.app.create_runtime_app",
        autospec=True,
        return_value=expected_app,
    )
    create_meta_file = mocker.patch(
        "mpt_extension_sdk.runtime.runner.create_meta_file",
        autospec=True,
    )
    get_runtime_settings = mocker.patch(
        "mpt_extension_sdk.settings.runtime.get_runtime_settings",
        autospec=True,
        return_value=runtime_settings,
    )
    mocker.patch(
        "mpt_extension_sdk.runtime.bootstrap.registration.register_instance_on_reload",
        autospec=True,
    )
    sys.modules.pop("mpt_extension_sdk.runtime.main", None)

    result = importlib.import_module("mpt_extension_sdk.runtime.main")

    assert result.app is expected_app
    get_runtime_settings.assert_called_once_with()
    create_meta_file.assert_called_once_with(runtime_settings)
    create_runtime_app.assert_called_once_with(runtime_settings=runtime_settings)


def test_main_registers_again_on_reload(runtime_settings, main_patches):
    reloading_settings = replace(runtime_settings, ziti_reload=True)
    register = main_patches(reloading_settings)

    importlib.import_module("mpt_extension_sdk.runtime.main")  # act

    register.assert_called_once_with(reloading_settings)


def test_main_skips_registration_without_reload(runtime_settings, main_patches):
    register = main_patches(replace(runtime_settings, ziti_reload=False))

    importlib.import_module("mpt_extension_sdk.runtime.main")  # act

    register.assert_not_called()
