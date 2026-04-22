import asyncio
from collections.abc import Callable

import pytest

from mpt_extension_sdk.services.mpt_api_service.subscription import SubscriptionService


@pytest.fixture
def subscription_client_mock(mocker, async_mpt_client):
    def factory():
        subscription_client = async_mpt_client.commerce.subscriptions
        return SubscriptionService(async_mpt_client), subscription_client

    return factory


def test_create(mocker, subscription_client_mock):
    api_subscription = mocker.Mock()
    service, subscription_client = subscription_client_mock()
    subscription_client.create = mocker.AsyncMock(return_value=api_subscription)
    from_payload = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.subscription.Subscription.from_payload",
        autospec=True,
        return_value="subscription-model",
    )

    result = asyncio.run(service.create({"name": "SUB-1"}))

    assert result == "subscription-model"
    subscription_client.create.assert_awaited_once_with({"name": "SUB-1"})
    from_payload.assert_called_once_with(api_subscription)


def test_get_by_id(mocker, subscription_client_mock):
    api_subscription = mocker.Mock()
    service, subscription_client = subscription_client_mock()
    subscription_client.get = mocker.AsyncMock(return_value=api_subscription)
    from_payload = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.subscription.Subscription.from_payload",
        autospec=True,
        return_value="subscription-model",
    )

    result = asyncio.run(service.get_by_id("SUB-1"))

    assert result == "subscription-model"
    subscription_client.get.assert_awaited_once_with("SUB-1")
    from_payload.assert_called_once_with(api_subscription)


def test_update(mocker, subscription_client_mock):
    service, subscription_client = subscription_client_mock()
    subscription_client.update = mocker.AsyncMock(spec=Callable)

    asyncio.run(service.update("SUB-1", {"description": "fake"}))  # act

    subscription_client.update.assert_awaited_once_with("SUB-1", {"description": "fake"})
