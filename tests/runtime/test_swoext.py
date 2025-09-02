import click

from mpt_extension_sdk.runtime import swoext


def test_print_version_prints_and_exits(mocker):
    ctx = mocker.Mock(autospec=True)
    ctx.resilient_parsing = False

    mock_echo = mocker.patch("mpt_extension_sdk.runtime.swoext.click.echo")

    swoext.print_version(ctx, None, value=True)

    assert mock_echo.call_count == 1
    ctx.exit.assert_called_once()


def test_print_version_no_value(mocker):
    ctx = mocker.Mock(autospec=True)
    ctx.resilient_parsing = False

    mock_echo = mocker.patch("mpt_extension_sdk.runtime.swoext.click.echo")

    result = swoext.print_version(ctx, None, value=False)

    assert mock_echo.call_count == 0
    ctx.exit.assert_not_called()
    assert result is None


def test_make_django_command_returns_click_command(mocker):
    cmd = swoext.make_django_command("shell", help_value="Test help")

    runner = click.testing.CliRunner()

    @click.command()
    def mock_command_func(*args, **kwargs):
        pass

    mocker.patch("mpt_extension_sdk.runtime.commands.django.django", mock_command_func)

    result = runner.invoke(cmd, ["arg1", "arg2"])

    assert result.exit_code == 0 or result.exit_code is None
    assert isinstance(cmd, click.Command)


def test_main_calls_cli(mocker):
    mock_cli = mocker.patch("mpt_extension_sdk.runtime.swoext.cli", new=mocker.Mock())

    swoext.main()

    mock_cli.assert_called_once_with(standalone_mode=False)
