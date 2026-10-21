from collections.abc import Callable

import pytest


@pytest.fixture
def async_route_handler(mocker):
    return mocker.AsyncMock(spec=Callable)


@pytest.fixture
def route_handler(mocker):
    return mocker.Mock(spec=Callable)
