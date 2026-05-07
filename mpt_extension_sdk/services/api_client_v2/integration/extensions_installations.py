from mpt_api_client.http import AsyncService
from mpt_api_client.http.mixins import AsyncCreateMixin
from mpt_api_client.models import Model


class IntegrationInstallations(Model):
    """Integration installations model."""


class IntegrationInstallationsServiceConfig:
    """Integration installations service config."""

    _endpoint = "/public/v1/integration/installations/-/token"
    _model_class = IntegrationInstallations


class AsyncIntegrationInstallationsService(
    AsyncCreateMixin[IntegrationInstallations],
    AsyncService[IntegrationInstallations],
    IntegrationInstallationsServiceConfig,
):
    """Extensions installations service."""
