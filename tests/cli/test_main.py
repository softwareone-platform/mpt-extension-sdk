from dataclasses import replace

import pytest
from typer.testing import CliRunner

from mpt_extension_sdk.cli.main import app
from mpt_extension_sdk.errors.runtime import ConfigError
from mpt_extension_sdk.runtime.models import MetaConfig, MetaEvent


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def matching_meta():
    return MetaConfig(
        version="1.0.0",
        openapi="/bypass/openapi.json",
        events=[
            MetaEvent(
                event="OrderPurchased",
                condition=None,
                path="/events/orders/purchase",
                task=False,
            )
        ],
    )


@pytest.fixture
def runtime_settings_factory(runtime_settings):
    def factory(**changes):
        return replace(runtime_settings, **changes)

    return factory


def test_run_command_uses_local_flag(cli_runner, mocker):
    mock_run_extension = mocker.patch("mpt_extension_sdk.cli.main.run_extension", autospec=True)

    result = cli_runner.invoke(app, ["run", "--local"])

    assert result.exit_code == 0
    mock_run_extension.assert_called_once_with(local=True)


def test_run_command_defaults_to_platform_mode(cli_runner, mocker):
    mock_run_extension = mocker.patch("mpt_extension_sdk.cli.main.run_extension", autospec=True)

    result = cli_runner.invoke(app, ["run"])

    assert result.exit_code == 0
    mock_run_extension.assert_called_once_with(local=False)


def test_meta_generate_writes_meta_file(runtime_settings_factory, cli_runner, mocker, tmp_path):
    meta = mocker.Mock(spec=MetaConfig)
    settings = runtime_settings_factory(meta_config=meta, meta_file_path=tmp_path / "meta.yaml")
    mocker.patch(
        "mpt_extension_sdk.cli.main.RuntimeSettings.load", autospec=True, return_value=settings
    )

    result = cli_runner.invoke(app, ["meta", "generate"])

    assert result.exit_code == 0
    settings.meta_config.to_file.assert_called_once_with(settings.meta_file_path)


def test_validate_succeeds_when_meta_matches(
    runtime_settings_factory, cli_runner, matching_meta, mocker, tmp_path
):
    settings = runtime_settings_factory(
        meta_config=matching_meta, meta_file_path=tmp_path / "meta.yaml"
    )
    mocker.patch(
        "mpt_extension_sdk.cli.main.RuntimeSettings.load", autospec=True, return_value=settings
    )
    mocker.patch(
        "mpt_extension_sdk.cli.main.MetaConfig.from_file", autospec=True, return_value=matching_meta
    )

    result = cli_runner.invoke(app, ["meta", "validate"])

    assert result.exit_code == 0
    assert "Metadata is valid" in result.stdout


def test_validate_generates_missing_meta_file(
    runtime_settings_factory, cli_runner, mocker, tmp_path
):
    meta = mocker.Mock(spec=MetaConfig)
    settings = runtime_settings_factory(meta_config=meta, meta_file_path=tmp_path / "meta.yaml")
    mocker.patch(
        "mpt_extension_sdk.cli.main.RuntimeSettings.load", autospec=True, return_value=settings
    )
    mocker.patch(
        "mpt_extension_sdk.cli.main.MetaConfig.from_file",
        autospec=True,
        side_effect=ConfigError("missing"),
    )

    result = cli_runner.invoke(app, ["meta", "validate"])

    assert result.exit_code == 1
    generated_path = tmp_path / "meta.generated.yaml"
    meta.to_file.assert_called_once_with(generated_path)
    assert "Generated file written" in result.stderr


def test_validate_generates_diff_meta_file(runtime_settings_factory, cli_runner, mocker, tmp_path):
    generated = MetaConfig(
        version="1.0.0",
        openapi="/bypass/openapi.json",
        events=[
            MetaEvent(
                event="OrderPurchased", condition=None, path="/events/orders/purchase", task=False
            )
        ],
    )
    checked_in = MetaConfig(
        version="1.0.0",
        openapi="/bypass/openapi.json",
        events=[
            MetaEvent(event="OrderChanged", condition=None, path="/events/orders/change", task=True)
        ],
    )
    settings = runtime_settings_factory(
        meta_config=generated, meta_file_path=tmp_path / "meta.yaml"
    )
    to_file = mocker.patch.object(MetaConfig, "to_file", autospec=True)
    mocker.patch(
        "mpt_extension_sdk.cli.main.RuntimeSettings.load", autospec=True, return_value=settings
    )
    mocker.patch(
        "mpt_extension_sdk.cli.main.MetaConfig.from_file", autospec=True, return_value=checked_in
    )

    result = cli_runner.invoke(app, ["meta", "validate"])

    assert result.exit_code == 1
    to_file.assert_called_once_with(generated, tmp_path / "meta.generated.yaml")
    assert "does not match metadata generated" in result.stderr
