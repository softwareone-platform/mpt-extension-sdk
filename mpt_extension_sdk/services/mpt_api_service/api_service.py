from typing import Self

from mpt_extension_sdk.api.auth import AuthContext
from mpt_extension_sdk.services.api_client_v2.mpt_api_client import AsyncMPTClient
from mpt_extension_sdk.services.mpt_api_service.account_scoped_client import (
    AccountScopedAsyncMPTClient,
    AccountTokenProvider,
)
from mpt_extension_sdk.services.mpt_api_service.account_token import AccountTokenService
from mpt_extension_sdk.services.mpt_api_service.agreement import AgreementService
from mpt_extension_sdk.services.mpt_api_service.asset import AssetService
from mpt_extension_sdk.services.mpt_api_service.client_factory import build_mpt_client
from mpt_extension_sdk.services.mpt_api_service.installation import InstallationService
from mpt_extension_sdk.services.mpt_api_service.order import OrderService
from mpt_extension_sdk.services.mpt_api_service.product import (
    ProductItemService,
    ProductService,
)
from mpt_extension_sdk.services.mpt_api_service.subscription import SubscriptionService
from mpt_extension_sdk.services.mpt_api_service.task import TaskService
from mpt_extension_sdk.services.mpt_api_service.template import TemplateService
from mpt_extension_sdk.settings.runtime import RuntimeSettings, get_runtime_settings


class MPTAPIService:  # noqa: WPS215, WPS230
    """API service for Marketplace operations."""

    def __init__(self, client: AsyncMPTClient) -> None:
        """Initialize API service.

        Args:
            client: Shared MPT API client.
        """
        self.client = client
        self.agreements = AgreementService(client)
        self.assets = AssetService(client)
        self.account_token = AccountTokenService(client)
        self.installations = InstallationService(client)
        self.products = ProductService(client)
        self.product_items = ProductItemService(client)
        self.orders = OrderService(client)
        self.subscriptions = SubscriptionService(client)
        self.tasks = TaskService(client)
        self.templates = TemplateService(client)

    @classmethod
    async def from_auth_context(cls, base_url: str, auth: AuthContext) -> Self:
        """Create the service from the request authentication context."""
        runtime_settings = get_runtime_settings()
        return cls._build_account_scoped(
            base_url=base_url,
            runtime_settings=runtime_settings,
            extension_id=auth.extension_id,
            account_id=auth.account.id,
        )

    @classmethod
    async def from_account_id(cls, base_url: str, account_id: str) -> Self:
        """Create the service authenticated against a specific account.

        Used by handlers that need to call the MPT API as a specific account
        (for example the Operations account) without a request authentication
        context. The extension identity is resolved from runtime settings.

        Args:
            base_url: MPT API base URL.
            account_id: Target Marketplace account id to authenticate as.
        """
        runtime_settings = get_runtime_settings()
        return cls._build_account_scoped(
            base_url=base_url,
            runtime_settings=runtime_settings,
            extension_id=runtime_settings.extension_id,
            account_id=account_id,
        )

    @classmethod
    def from_config(cls, base_url: str, api_token: str) -> Self:
        """Create the service from connection settings.

        Args:
            base_url: MPT API base URL.
            api_token: MPT API token.
        """
        return cls(build_mpt_client(base_url=base_url, api_token=api_token))

    @classmethod
    def _build_account_scoped(
        cls,
        *,
        base_url: str,
        runtime_settings: RuntimeSettings,
        extension_id: str,
        account_id: str,
    ) -> Self:
        client = AccountScopedAsyncMPTClient.from_token_provider(
            base_url=base_url,
            bootstrap_api_token=runtime_settings.ext_api_key,
            token_provider=AccountTokenProvider(
                runtime_settings=runtime_settings,
                extension_id=extension_id,
                account_id=account_id,
                service_type=cls,
            ),
        )
        return cls(client)
