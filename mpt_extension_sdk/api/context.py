from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from mpt_extension_sdk.context import BaseContext

if TYPE_CHECKING:
    from mpt_extension_sdk.api.auth import AuthContext, AuthenticatedRequestContext
    from mpt_extension_sdk.services.mpt_api_service import MPTAPIService


@dataclass(kw_only=True)
class AuthenticatedContext(BaseContext):
    """Base context shared by authenticated route families."""

    auth: "AuthContext"
    request: "AuthenticatedRequestContext"

    state: dict[str, Any] = field(default_factory=dict)


@dataclass(kw_only=True)
class APIContext(AuthenticatedContext):
    """Execution context passed to authenticated API handlers."""

    mpt_api_service: "MPTAPIService"
