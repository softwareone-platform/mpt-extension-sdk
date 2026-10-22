from collections.abc import Callable

import pytest

from mpt_extension_sdk.routing import only_deferrable
from mpt_extension_sdk.routing.decorators import is_only_deferrable


@pytest.fixture
def route_handler(mocker):
    return mocker.AsyncMock(spec=Callable, return_value=None)


def test_only_deferrable_marks_wrapper(route_handler):
    result = only_deferrable(route_handler)

    assert result is not route_handler
    assert result.__wrapped__ is route_handler
    assert is_only_deferrable(result) is True


def test_only_deferrable_keeps_handler_unmarked(route_handler):
    only_deferrable(route_handler)  # act

    assert is_only_deferrable(route_handler) is False


async def test_only_deferrable_calls_handler(route_handler):
    result = await only_deferrable(route_handler)("ctx", body="body")

    assert result is None
    route_handler.assert_awaited_once_with("ctx", body="body")
