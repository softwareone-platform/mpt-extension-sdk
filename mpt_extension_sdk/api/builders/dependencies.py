from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from mpt_extension_sdk.services.mpt_api_service.api_service import MPTAPIService
from mpt_extension_sdk.services.mpt_api_service.task import TaskService
from mpt_extension_sdk.settings.runtime import RuntimeSettings, get_runtime_settings


def get_tasks_service(
    runtime_settings: Annotated[RuntimeSettings, Depends(get_runtime_settings)],
) -> TaskService:
    """Return the task service authenticated with the extension token."""
    return _cached_tasks_service(
        base_url=runtime_settings.mpt_api_base_url,
        api_token=runtime_settings.ext_api_key,
    )


@lru_cache(maxsize=4)
def _cached_tasks_service(*, base_url: str, api_token: str) -> TaskService:
    """Build the task service once per configuration, reusing its HTTP client."""
    return MPTAPIService.from_config(base_url=base_url, api_token=api_token).tasks
