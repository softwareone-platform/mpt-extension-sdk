from dataclasses import dataclass

import pytest

from mpt_extension_sdk.errors.runtime import ConfigError
from mpt_extension_sdk.settings.extension import (
    BaseExtensionSettings,
    get_extension_settings,
    load_extension_settings,
)


@dataclass(frozen=True)
class FakeExtensionSettings(BaseExtensionSettings):
    sample: str

    @classmethod
    def load(cls):
        return cls(sample="loaded")


@pytest.fixture(autouse=True)
def clear_extension_settings_cache():
    load_extension_settings.cache_clear()
    yield
    load_extension_settings.cache_clear()


def test_load_extension_settings_requires_name():
    with pytest.raises(ConfigError, match="module name cannot be empty"):
        load_extension_settings("")


def test_load_extension_settings_imports_class(mocker):
    load = mocker.patch.object(
        FakeExtensionSettings,
        "load",
        autospec=True,
        return_value=FakeExtensionSettings(sample="loaded"),
    )
    mocker.patch(
        "mpt_extension_sdk.settings.extension.import_module",
        autospec=True,
        return_value=mocker.Mock(ExtensionSettings=FakeExtensionSettings),
    )

    result = load_extension_settings("mock_ext.settings")

    assert result == FakeExtensionSettings(sample="loaded")
    load.assert_called_once_with()


def test_load_extension_settings_rejects_module(mocker):
    error = ModuleNotFoundError("missing")
    error.name = "missing.settings"
    mocker.patch(
        "mpt_extension_sdk.settings.extension.import_module",
        autospec=True,
        side_effect=error,
    )

    with pytest.raises(ConfigError, match="was not found"):
        load_extension_settings("missing.settings")


def test_load_extension_settings_reraises_error(mocker):
    error = ModuleNotFoundError("nested")
    error.name = "nested.dep"
    mocker.patch(
        "mpt_extension_sdk.settings.extension.import_module",
        autospec=True,
        side_effect=error,
    )

    with pytest.raises(ModuleNotFoundError, match="nested"):
        load_extension_settings("mock_ext.settings")


def test_load_extension_rejects_missing_class(mocker):
    mocker.patch(
        "mpt_extension_sdk.settings.extension.import_module",
        autospec=True,
        return_value=mocker.Mock(spec=[]),
    )

    with pytest.raises(ConfigError, match="must define ExtensionSettings"):
        load_extension_settings("mock_ext.settings")


def test_load_extension_rejects_invalid_class(mocker):
    mocker.patch(
        "mpt_extension_sdk.settings.extension.import_module",
        autospec=True,
        return_value=mocker.Mock(ExtensionSettings=object),
    )

    with pytest.raises(ConfigError, match="must inherit from BaseExtensionSettings"):
        load_extension_settings("mock_ext.settings")


def test_get_extension_settings_uses_module(mocker):
    runtime_settings = mocker.Mock(settings_module="mock_ext.settings")
    get_runtime_settings = mocker.patch(
        "mpt_extension_sdk.settings.extension.get_runtime_settings",
        autospec=True,
        return_value=runtime_settings,
    )
    load_extension = mocker.patch(
        "mpt_extension_sdk.settings.extension.load_extension_settings",
        autospec=True,
        return_value=FakeExtensionSettings(sample="loaded"),
    )

    result = get_extension_settings()

    assert result == FakeExtensionSettings(sample="loaded")
    get_runtime_settings.assert_called_once_with()
    load_extension.assert_called_once_with("mock_ext.settings")
