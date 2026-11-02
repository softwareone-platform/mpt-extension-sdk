import asyncio

import pytest

from mpt_extension_sdk.api.builders.handlers import resolve_handler_result


@pytest.fixture
def async_handler():
    async def resolve(result):  # noqa: WPS430
        await asyncio.sleep(0)
        return result

    return resolve


@pytest.fixture
def failing_async_handler():
    async def fail():  # noqa: WPS430
        await asyncio.sleep(0)
        raise ValueError("async boom")

    return fail


async def test_resolve_handler_result_awaits_coroutine(async_handler):
    result = await resolve_handler_result(async_handler("async-result"))

    assert result == "async-result"


async def test_resolve_handler_result_returns_value():
    result = await resolve_handler_result("sync-result")

    assert result == "sync-result"


async def test_resolve_handler_result_propagates_error(failing_async_handler):
    with pytest.raises(ValueError, match="async boom"):
        await resolve_handler_result(failing_async_handler())
