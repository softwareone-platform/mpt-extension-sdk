from dataclasses import dataclass

from mpt_extension_sdk.api.auth import AuthContext, AuthenticationError
from mpt_extension_sdk.context import BaseContext
from mpt_extension_sdk.pipeline.builders.base import ContextBuilder, ContextResources
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.settings.extension import get_extension_settings
from mpt_extension_sdk.settings.runtime import get_runtime_settings


@dataclass(frozen=True)
class RouteContextFactory:
    """Factory for building execution contexts across route families.

    The process-wide settings are read on each build, so a factory can be created
    when the routes are registered, before the runtime settings are loaded.
    """

    service_type: type[MPTAPIService] = MPTAPIService

    async def build[ContextT: BaseContext](
        self, builder: ContextBuilder[ContextT], auth: AuthContext
    ) -> ContextT:
        """Build an execution context with the resources of an authenticated call.

        Args:
            builder: Builder of the context of the route family.
            auth: Authenticated request claims.

        Returns:
            The context built by `builder`.

        Raises:
            AuthenticationError: When the token targets another extension.
        """
        runtime_settings = get_runtime_settings()
        if auth.extension_id != runtime_settings.extension_id:
            raise AuthenticationError
        base_url = runtime_settings.mpt_api_base_url
        return await builder.build(
            ContextResources(
                auth=auth,
                ext_settings=get_extension_settings(),
                mpt_api_service=await self.service_type.from_auth_context(
                    base_url=base_url, auth=auth
                ),
                runtime_settings=runtime_settings,
                vendor_mpt_api_service=await self.service_type.from_vendor_account(
                    base_url=base_url
                ),
            )
        )
