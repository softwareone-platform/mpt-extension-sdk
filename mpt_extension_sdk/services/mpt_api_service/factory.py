from mpt_extension_sdk.services.mpt_api_service.account_scoped import (
    AccountScopedMPTAPIService,
    AccountTokenProvider,
)
from mpt_extension_sdk.services.mpt_api_service.api_service import MPTAPIService
from mpt_extension_sdk.settings.runtime import RuntimeSettings


class MPTAPIServiceFactory:
    """Factory responsible for constructing route-scoped MPT API services."""

    def __init__(
        self,
        *,
        runtime_settings: RuntimeSettings,
        service_type: type[MPTAPIService] = MPTAPIService,
    ) -> None:
        self._runtime_settings = runtime_settings
        self._service_type = service_type

    def build_runtime_service(self) -> MPTAPIService:
        """Build the default runtime-scoped service used by event routes today."""
        return self._service_type.from_config(
            base_url=self._runtime_settings.mpt_api_base_url,
            api_token=self._runtime_settings.mpt_api_token,
        )

    def build_account_scoped_service(self, account_id: str) -> AccountScopedMPTAPIService:
        """Build the account-scoped service used by authenticated route families."""
        return AccountScopedMPTAPIService(
            service_type=self._service_type,
            base_url=self._runtime_settings.mpt_api_base_url,
            token_provider=AccountTokenProvider(
                self._runtime_settings,
                account_id,
                service_type=self._service_type,
            ),
        )
