from pathlib import Path

import pytest

from mpt_extension_sdk.errors.runtime import ConfigError
from mpt_extension_sdk.settings.runtime import (
    DEFAULT_LOCAL_PORT,
    RuntimeSettings,
    get_runtime_settings,
)


class FakeExtensionApp:
    def __init__(self, meta_config):
        self._meta_config = meta_config

    def to_meta_config(self):
        return self._meta_config


class FakeInvalidMetaApp:
    def to_meta_config(self):
        return object()


@pytest.fixture
def runtime_env(mocker):
    mocker.patch.dict(
        "os.environ",
        {
            "SDK_EXTENSION_URL": "https://extensions.example.com",
            "SDK_EXTENSION_API_KEY": "extension-api-key",
            "SDK_EXTENSION_ID": "EXT-1",
            "MPT_API_BASE_URL": "https://api.example.com",
        },
        clear=True,
    )


@pytest.fixture
def fake_package(tmp_path):
    package_dir = tmp_path / "mock_ext"
    package_dir.mkdir()
    (package_dir / "app.py").write_text("", encoding="utf-8")
    (package_dir / "settings.py").write_text("", encoding="utf-8")
    return package_dir


@pytest.fixture
def settings_loader_state(mocker, tmp_path):
    mocker.patch(
        "mpt_extension_sdk.settings.runtime.Path.cwd",
        autospec=True,
        return_value=tmp_path,
    )
    get_runtime_settings.cache_clear()
    yield
    get_runtime_settings.cache_clear()


def test_extension_package(runtime_settings):
    result = runtime_settings.extension_package

    assert result == "mock_app"


def test_load_reads_runtime_env(
    mocker, runtime_env, settings_loader_state, fake_package, meta_config
):
    mocker.patch(
        "mpt_extension_sdk.settings.runtime.import_module",
        autospec=True,
        return_value=mocker.Mock(ext_app=FakeExtensionApp(meta_config)),
    )
    mocker.patch(
        "mpt_extension_sdk.settings.runtime.socket.gethostname",
        autospec=True,
        return_value="host-1",
    )

    result = RuntimeSettings.load()

    assert (
        result.app_module,
        result.settings_module,
        result.ext_api_key,
        result.base_url,
        result.extension_id,
        result.mpt_api_base_url,
        result.external_id,
        result.identity_file_path,
    ) == (
        "mock_ext.app",
        "mock_ext.settings",
        "extension-api-key",
        "https://extensions.example.com",
        "EXT-1",
        "https://api.example.com",
        "host-1",
        Path.cwd() / "host-1_identity.json",
    )
    assert result.meta_config == meta_config
    assert (
        result.meta_file_path,
        result.log_level,
        result.observability_enabled,
        result.applicationinsights_connection_string,
        result.otel_service_name,
        result.otel_otlp_endpoint,
        result.local_host,
        result.local_port,
        result.local_reload,
        result.local_workers,
        result.ziti_workers,
        result.ziti_reload,
    ) == (
        Path.cwd() / "meta.yaml",
        "INFO",
        True,
        "",
        "",
        "",
        "0.0.0.0",
        DEFAULT_LOCAL_PORT,
        True,
        1,
        4,
        False,
    )


def test_load_uses_explicit_runtime_overrides(
    mocker, runtime_env, settings_loader_state, fake_package, meta_config
):
    mocker.patch.dict(
        "os.environ",
        {
            "SDK_EXTENSION_EXTERNAL_ID": "ext-123",
            "SDK_IDENTITY_FILE_PATH": "/tmp/custom-identity.json",
            "LOG_LEVEL": "DEBUG",
            "SDK_OBSERVABILITY_ENABLED": "false",
            "SDK_APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=test",
            "SDK_OTEL_SERVICE_NAME": "svc",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://jaeger:4318",
            "SDK_LOCAL_HOST": "127.0.0.1",
            "SDK_LOCAL_PORT": "9000",
            "SDK_LOCAL_RELOAD": "false",
            "SDK_LOCAL_WORKERS": "3",
            "SDK_ZITI_WORKERS": "8",
            "SDK_ZITI_RELOAD": "true",
        },
    )
    mocker.patch(
        "mpt_extension_sdk.settings.runtime.import_module",
        autospec=True,
        return_value=mocker.Mock(ext_app=FakeExtensionApp(meta_config)),
    )

    result = RuntimeSettings.load()

    assert (
        result.external_id,
        result.identity_file_path,
        result.log_level,
        result.observability_enabled,
        result.applicationinsights_connection_string,
        result.otel_service_name,
        result.otel_otlp_endpoint,
        result.local_host,
        result.local_port,
        result.local_reload,
        result.local_workers,
        result.ziti_workers,
        result.ziti_reload,
    ) == (
        "ext-123",
        Path("/tmp/custom-identity.json"),
        "DEBUG",
        False,
        "InstrumentationKey=test",
        "svc",
        "http://jaeger:4318",
        "127.0.0.1",
        9000,
        False,
        3,
        8,
        True,
    )


def test_load_prefers_traces_otlp_endpoint(
    mocker, runtime_env, settings_loader_state, fake_package, meta_config
):
    mocker.patch.dict(
        "os.environ",
        {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://generic:4318",
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "http://traces:4318",
        },
    )
    mocker.patch(
        "mpt_extension_sdk.settings.runtime.import_module",
        autospec=True,
        return_value=mocker.Mock(ext_app=FakeExtensionApp(meta_config)),
    )

    result = RuntimeSettings.load()

    assert result.otel_otlp_endpoint == "http://traces:4318"


def test_load_uses_uuid_when_hostname_blank(
    mocker, runtime_env, settings_loader_state, fake_package, meta_config
):
    mocker.patch(
        "mpt_extension_sdk.settings.runtime.import_module",
        autospec=True,
        return_value=mocker.Mock(ext_app=FakeExtensionApp(meta_config)),
    )
    mocker.patch(
        "mpt_extension_sdk.settings.runtime.socket.gethostname",
        autospec=True,
        return_value=" ",
    )
    mocker.patch(
        "mpt_extension_sdk.settings.runtime.uuid.getnode",
        autospec=True,
        return_value=0xABC,
    )

    result = RuntimeSettings.load()

    assert result.external_id == "000000000abc"
    assert result.identity_file_path == Path.cwd() / "000000000abc_identity.json"


def test_load_rejects_missing_extension_app(
    mocker, runtime_env, settings_loader_state, fake_package
):
    mocker.patch(
        "mpt_extension_sdk.settings.runtime.import_module",
        autospec=True,
        return_value=mocker.Mock(spec=[]),
    )

    with pytest.raises(ConfigError, match="must export 'ext_app'"):
        RuntimeSettings.load()


def test_load_rejects_missing_meta_factory(
    mocker, runtime_env, settings_loader_state, fake_package
):
    mocker.patch(
        "mpt_extension_sdk.settings.runtime.import_module",
        autospec=True,
        return_value=mocker.Mock(ext_app=object()),
    )

    with pytest.raises(ConfigError, match="does not expose metadata generation"):
        RuntimeSettings.load()


def test_load_rejects_invalid_meta_type(mocker, runtime_env, settings_loader_state, fake_package):
    mocker.patch(
        "mpt_extension_sdk.settings.runtime.import_module",
        autospec=True,
        return_value=mocker.Mock(ext_app=FakeInvalidMetaApp()),
    )

    with pytest.raises(ConfigError, match="must be a MetaConfig instance"):
        RuntimeSettings.load()


def test_load_rejects_missing_package(mocker, runtime_env, settings_loader_state):
    mocker.patch(
        "mpt_extension_sdk.settings.runtime.import_module",
        autospec=True,
    )

    with pytest.raises(ConfigError, match="Unable to autodiscover the extension package"):
        RuntimeSettings.load()


def test_load_rejects_multiple_packages(
    mocker, runtime_env, settings_loader_state, tmp_path, meta_config
):
    for package_name in ("pkg_one", "pkg_two"):
        package_dir = tmp_path / package_name
        package_dir.mkdir()
        (package_dir / "app.py").write_text("", encoding="utf-8")
        (package_dir / "settings.py").write_text("", encoding="utf-8")
    mocker.patch(
        "mpt_extension_sdk.settings.runtime.import_module",
        autospec=True,
        return_value=mocker.Mock(ext_app=FakeExtensionApp(meta_config)),
    )

    with pytest.raises(ConfigError, match="Unable to autodiscover the extension package"):
        RuntimeSettings.load()


def test_get_runtime_settings_caches_load(mocker, runtime_settings):
    load = mocker.patch.object(
        RuntimeSettings,
        "load",
        autospec=True,
        return_value=runtime_settings,
    )
    get_runtime_settings.cache_clear()

    result = (get_runtime_settings(), get_runtime_settings())

    assert result == (runtime_settings, runtime_settings)
    load.assert_called_once_with()
    get_runtime_settings.cache_clear()
