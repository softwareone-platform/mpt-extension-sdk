import pytest

from mpt_extension_sdk.runtime import runner
from mpt_extension_sdk.runtime.models import MetaConfig
from mpt_extension_sdk.settings.runtime import RuntimeSettings


@pytest.fixture
def runner_patches(mocker, runtime_settings):
    mocker.patch.object(
        runner, "get_runtime_settings", autospec=True, return_value=runtime_settings
    )

    return {
        "create_meta_file": mocker.patch.object(runner, "create_meta_file", autospec=True),
        "run_fastapi": mocker.patch.object(runner, "run_fastapi", autospec=True),
        "register_instance": mocker.patch.object(runner, "register_instance", autospec=True),
        "run_ziti": mocker.patch.object(runner, "run_ziti", autospec=True),
    }


def test_run_extension_local_mode(runtime_settings, runner_patches):
    create_meta_file = runner_patches["create_meta_file"]
    run_fastapi = runner_patches["run_fastapi"]
    register_instance = runner_patches["register_instance"]
    run_ziti = runner_patches["run_ziti"]

    runner.run_extension(local=True)  # act

    create_meta_file.assert_called_once_with(runtime_settings)
    run_fastapi.assert_called_once_with(
        "mpt_extension_sdk.runtime.main:app",
        host=runtime_settings.local_host,
        port=runtime_settings.local_port,
        reload=runtime_settings.local_reload,
        workers=runtime_settings.local_workers,
    )
    run_ziti.assert_not_called()
    register_instance.assert_not_called()


def test_run_extension_platform_mode(runtime_settings, runner_patches):
    create_meta_file = runner_patches["create_meta_file"]
    run_fastapi = runner_patches["run_fastapi"]
    register_instance = runner_patches["register_instance"]
    run_ziti = runner_patches["run_ziti"]

    runner.run_extension(local=False)  # act

    create_meta_file.assert_called_once_with(runtime_settings)
    register_instance.assert_called_once_with(settings=runtime_settings)
    run_ziti.assert_called_once_with(
        "mpt_extension_sdk.runtime.main:app",
        runtime_settings.identity_file_path,
        reload=runtime_settings.ziti_reload,
        workers=runtime_settings.ziti_workers,
    )
    run_fastapi.assert_not_called()


def test_create_meta_file_persists_config(mocker, runtime_settings):
    settings = mocker.Mock(
        spec=RuntimeSettings,
        meta_config=mocker.Mock(spec=MetaConfig),
        meta_file_path=runtime_settings.meta_file_path,
    )

    runner.create_meta_file(settings)  # act

    settings.meta_config.to_file.assert_called_once_with(runtime_settings.meta_file_path)


def test_run_ziti_passes_expected_arguments(mocker, tmp_path):
    ziticorn_run = mocker.patch.object(runner.ziticorn, "run", autospec=True)

    runner.run_ziti("module:app", tmp_path / "identity.json", reload=True, workers=7)  # act

    ziticorn_run.assert_called_once_with(
        "module:app",
        str(tmp_path / "identity.json"),
        server_reload=True,
        server_workers=7,
        ziti_load_timeout_ms=runner.DEFAULT_ZITI_LOAD_TIMEOUT_MS,
    )


def test_run_fastapi_passes_expected_arguments(mocker):
    uvicorn_run = mocker.patch.object(runner.uvicorn, "run", autospec=True)

    runner.run_fastapi("module:app", "127.0.0.1", 9000, reload=False, workers=2)  # act

    uvicorn_run.assert_called_once_with("module:app", host="127.0.0.1", port=9000, workers=2)
