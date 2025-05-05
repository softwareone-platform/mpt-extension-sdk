from mpt_extension_sdk.key_vault.base import KeyVault


def test_init_key_vault(mock_key_vault_name):
    key_vault = KeyVault(mock_key_vault_name)
    assert key_vault.key_vault_name == mock_key_vault_name


def test_get_secret(mocker, mock_key_vault_name, mock_secret_name, mock_key_vault_url):
    key_vault = KeyVault(mock_key_vault_name)
    mock_secret_value = mocker.MagicMock()
    mock_secret_value.value = "mock_secret_value"
    mock_client = mocker.MagicMock()
    mocker.patch.object(key_vault, "_get_key_vault_client", return_value=mock_client)
    mocker.patch.object(
        key_vault, "_get_key_vault_url", return_value=mock_key_vault_url
    )
    mocker.patch.object(mock_client, "get_secret", return_value=mock_secret_value)
    secret = key_vault.get_secret(mock_secret_name)
    assert secret == mock_secret_value.value


def test_set_secret(mocker, mock_key_vault_name, mock_secret_name, mock_key_vault_url):
    key_vault = KeyVault(mock_key_vault_name)
    mock_secret_value = mocker.MagicMock()
    mock_secret_value.value = "mock_secret_value"
    mock_client = mocker.MagicMock()
    mocker.patch.object(key_vault, "_get_key_vault_client", return_value=mock_client)
    mocker.patch.object(
        key_vault, "_get_key_vault_url", return_value=mock_key_vault_url
    )
    mocker.patch.object(mock_client, "set_secret", return_value=mock_secret_value.value)
    mocker.patch.object(mock_client, "get_secret", return_value=mock_secret_value)
    secret = key_vault.get_secret(mock_secret_name)
    assert secret == mock_secret_value.value
