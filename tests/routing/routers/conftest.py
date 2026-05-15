from collections.abc import Callable

import pytest


@pytest.fixture
def route_handler(mocker):
    return mocker.Mock(spec=Callable)
