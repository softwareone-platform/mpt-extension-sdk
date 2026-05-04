from mpt_extension_sdk.api.auth import AuthContext
from mpt_extension_sdk.api.context import APIContext
from mpt_extension_sdk.api.errors import UnauthorizedError


class APIRequestValidator:
    """Validate authenticated API request invariants after context construction."""

    @classmethod
    def assert_extension_id_matches(cls, auth_context: AuthContext, context: APIContext) -> None:
        """Ensure the caller token targets the configured extension."""
        if auth_context.extension_id != context.runtime_settings.extension_id:
            raise UnauthorizedError
