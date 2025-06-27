import pytest

from mpt_extension_sdk.mpt_http.base import MPTClient


@pytest.fixture()
def mock_mpt_client(mocker):
    """
    Create an instance of the MPT client used by the extension.
    """
    return mocker.MagicMock(spec=MPTClient)


@pytest.fixture()
def mock_get_agreements_by_query(mocker):
    return mocker.patch(
        "mpt_extension_sdk.mpt_http.mpt.get_agreements_by_query",
        spec=True,
    )


@pytest.fixture(scope="session")
def notify_post_resp():
    return {
        "$meta": {"omitted": ["attachments"]},
        "id": "MST-0000-0000-0001",
        "category": {
            "id": "NTC-0000-0002",
            "shortDescription": "Stay informed about important changes to your account",
            "status": "Published",
            "name": "Account",
        },
        "account": {
            "id": "ACC-0000-0001",
            "type": "Operations",
            "status": "Active",
            "name": "Adastraflex",
        },
        "subject": "Hello world",
        "body": "Hello world",
        "audit": {
            "created": {
                "at": "2025-04-23T08:40:22.248Z",
                "by": {
                    "id": "USR-0000-0001",
                    "name": "will.smith@adastraflex.com",
                    "icon": "/v1/accounts/users/USR-0000-0001/icon",
                },
            },
            "updated": {
                "at": "2025-04-23T08:40:22.248Z",
                "by": {
                    "id": "USR-0000-0001",
                    "name": "will.smith@adastraflex.com",
                    "icon": "/v1/accounts/users/USR-0000-0001/icon",
                },
            },
        },
    }
