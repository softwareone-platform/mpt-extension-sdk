from fastapi import FastAPI

from mpt_extension_sdk.runtime.app import create_runtime_app
from mpt_extension_sdk.runtime.runner import create_meta_file
from mpt_extension_sdk.settings.runtime import get_runtime_settings


def bootstrap_runtime_app() -> FastAPI:
    """Build the ASGI app and persist meta.yaml on every uvicorn import."""
    settings = get_runtime_settings()
    create_meta_file(settings)
    return create_runtime_app(runtime_settings=settings)


app = bootstrap_runtime_app()
