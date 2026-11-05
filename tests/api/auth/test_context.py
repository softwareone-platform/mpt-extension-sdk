from mpt_extension_sdk.api.auth import Account, AccountType


def test_account_is_client():
    account = Account(id="client", type=AccountType.CLIENT)

    result = account.is_client()

    assert result is True


def test_account_is_operations():
    account = Account(id="operation", type=AccountType.OPERATIONS)

    result = account.is_operations()

    assert result is True


def test_account_is_vendor():
    account = Account(id="vendor", type=AccountType.VENDOR)

    result = account.is_vendor()

    assert result is True
