from mpt_api_client.http import AsyncService
from mpt_api_client.http.mixins import AsyncCreateMixin
from mpt_api_client.models import Model


class IntegrationInstallationsToken(Model):
    """Integration installations token model."""


class IntegrationInstallationsTokenServiceConfig:
    """Integration installations token service config."""

    _endpoint = "/public/v1/integration/installations/-/token"
    _model_class = IntegrationInstallationsToken


class AsyncIntegrationInstallationsTokenService(
    AsyncCreateMixin[IntegrationInstallationsToken],
    AsyncService[IntegrationInstallationsToken],
    IntegrationInstallationsTokenServiceConfig,
):
    """Extensions installations token service."""
