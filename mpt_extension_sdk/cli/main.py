from typing import Annotated

import typer

from mpt_extension_sdk.errors.runtime import ConfigError
from mpt_extension_sdk.runtime.models import MetaConfig
from mpt_extension_sdk.runtime.runner import run_extension
from mpt_extension_sdk.settings.runtime import RuntimeSettings

app = typer.Typer(no_args_is_help=True, invoke_without_command=True)


@app.command()
def run(
    local: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--local", help="Run with Uvicorn (local development mode)"),
    ] = False,
) -> None:
    """Start the extension server."""
    run_extension(local=local)


meta_app = typer.Typer(no_args_is_help=True)
app.add_typer(meta_app, name="meta")


@meta_app.command("generate")
def generate_meta() -> None:
    """Generate the metadata file from the extension app."""
    runtime_settings = RuntimeSettings.load()
    runtime_settings.meta_config.to_file(runtime_settings.meta_file_path)
    typer.echo(f"Generated {runtime_settings.meta_file_path}")


@meta_app.command()
def validate() -> None:
    """Validate that the generated metadata matches the checked-in file."""
    runtime_settings = RuntimeSettings.load()
    generated_meta = runtime_settings.meta_config
    generated_path = runtime_settings.meta_file_path.with_name("meta.generated.yaml")
    try:
        checked_in_meta = MetaConfig.from_file(runtime_settings.meta_file_path)
    except ConfigError as error:
        generated_meta.to_file(generated_path)
        typer.secho(f"Failed to load checked-in meta.yaml: {error}", err=True, fg=typer.colors.RED)
        typer.secho(f"Generated file written to: {generated_path}", err=True)
        raise typer.Exit(code=1) from None

    if checked_in_meta != generated_meta:
        generated_meta.to_file(generated_path)
        typer.secho(
            "Checked-in meta.yaml does not match metadata generated from the extension app.",
            err=True,
            fg=typer.colors.RED,
        )
        typer.secho(f"Generated file written to: {generated_path}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Metadata is valid: {runtime_settings.meta_file_path}")


@app.callback()
def callback() -> None:
    """Callback for the CLI."""


def main() -> None:
    """Main entry point for the `mpt-ext` CLI."""
    app()


if __name__ == "__main__":
    main()
