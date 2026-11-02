from dataclasses import dataclass
from typing import Any

from mpt_extension_sdk.api.context import AuthenticatedRequestContext
from mpt_extension_sdk.context import BaseContext


@dataclass(kw_only=True)
class WebhookContext(BaseContext):
    """Execution context passed to webhook handlers."""

    payload: dict[str, Any]
    request: AuthenticatedRequestContext
