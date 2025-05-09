import logging

from azure.core.exceptions import (
    HttpResponseError,
    ResourceNotFoundError,
)
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from requests import Session

logger = logging.getLogger(__name__)


class KeyVault(Session):
    def __init__(self, key_vault_name: str):
        """
        Initialize the KeyVault client with the provided Key Vault name.

        Args:
            key_vault_name (str): The name of the Azure Key Vault.
        """
        super().__init__()
        self.key_vault_name = key_vault_name

    def get_secret(self, secret_name: str):
        """
        Retrieve a secret from the Azure Key Vault.

        Args:
            key_vault_url (str): The URL of the Azure Key Vault.
            secret_name (str): The name of the secret to retrieve.

        Returns:
            str: The value of the secret.
        """
        try:
            client = self._get_key_vault_client(self.key_vault_name)

            # Retrieve the secret from the Key Vault
            secret = client.get_secret(secret_name)

            return secret.value
        except ResourceNotFoundError as e:
            logger.error(
                f"Secret '{secret_name}' not found in Key Vault '{self.key_vault_name}': {e}"
            )
            return None

    def set_secret(self, secret_name: str, secret_value: str):
        """
        Set a secret in the Azure Key Vault.

        Args:
            key_vault_url (str): The URL of the Azure Key Vault.
            secret_name (str): The name of the secret to set.
            secret_value (str): The value of the secret to set.

        Returns:
            None
        """

        # Set the secret in the Key Vault
        try:
            client = self._get_key_vault_client(self.key_vault_name)

            client.set_secret(secret_name, secret_value)

            updated_secret = client.get_secret(secret_name)

            return updated_secret.value
        except HttpResponseError as e:
            logger.error(
                f"Failed to set secret '{secret_name}' in Key Vault '{self.key_vault_name}': {e}"
            )
            return None

    def _get_key_vault_url(self, key_vault_name: str):  # pragma: no cover
        """
        Construct the Key Vault URL using the provided Key Vault name.

        Args:
            key_vault_name (str): The name of the Azure Key Vault.

        Returns:
            str: The URL of the Azure Key Vault.
        """

        # Construct the Key Vault URL
        return f"https://{key_vault_name}.vault.azure.net/"

    def _get_key_vault_client(self, key_vault_name: str):  # pragma: no cover
        """
        Create a Key Vault client using the provided Key Vault URL and secret name.

        Args:
            key_vault_url (str): The URL of the Azure Key Vault.

        Returns:
            SecretClient: An instance of the SecretClient for the specified Key Vault.
        """

        # Get the Key Vault URL
        key_vault_url = self._get_key_vault_url(key_vault_name)
        # Create a credential object using DefaultAzureCredential
        credential = DefaultAzureCredential()

        # Create a Key Vault client using the credential
        client = SecretClient(vault_url=key_vault_url, credential=credential)

        return client
