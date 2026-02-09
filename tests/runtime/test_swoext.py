import click

from mpt_extension_sdk.runtime import swoext


def test_print_version_prints_and_exits(mocker):
    ctx = mocker.Mock(autospec=True)
    ctx.resilient_parsing = False
    mock_echo = mocker.patch("mpt_extension_sdk.runtime.swoext.click.echo", autospec=True)

    swoext.print_version(ctx, None, value=True)  # act

    mock_echo.assert_called_once()
    ctx.exit.assert_called_once()


def test_print_version_no_value(mocker):
    ctx = mocker.Mock(autospec=True)
    ctx.resilient_parsing = False
    mock_echo = mocker.patch("mpt_extension_sdk.runtime.swoext.click.echo", autospec=True)

    result = swoext.print_version(ctx, None, value=False)

    assert result is None
    mock_echo.assert_not_called()
    ctx.exit.assert_not_called()


def test_make_django_command_returns_click_command(mocker):
    cmd = swoext.make_django_command("shell", help_value="Test help")
    runner = click.testing.CliRunner()

    # BL
    @click.command()
    def mock_command_func(*args, **kwargs):
        pass

    # BL
    mocker.patch("mpt_extension_sdk.runtime.commands.django.django", mock_command_func)

    result = runner.invoke(cmd, ["arg1", "arg2"])

    assert result.exit_code == 0 or result.exit_code is None
    assert isinstance(cmd, click.Command)


def test_main_calls_cli(mocker):
    mock_cli = mocker.patch("mpt_extension_sdk.runtime.swoext.cli", autospec=True)

    swoext.main()  # act

    mock_cli.assert_called_once_with(standalone_mode=False)
