import pytest


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
