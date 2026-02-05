import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import pytest

from mpt_extension_sdk.core.events.dataclasses import Event
from mpt_extension_sdk.mpt_http.base import MPTClient
from mpt_extension_sdk.runtime.events.dispatcher import Dispatcher


@pytest.fixture(autouse=True)
def mock_time_sleep(mocker):
    mocker.patch("mpt_extension_sdk.runtime.events.dispatcher.time.sleep", autospec=True)


def test_dispatcher(mock_app_group_name):
    result = Dispatcher(group=mock_app_group_name)

    assert result is not None
    assert isinstance(result.client, MPTClient)
    assert isinstance(result.executor, ThreadPoolExecutor)
    assert isinstance(result.queue, deque)
    assert result.futures == {}
    assert isinstance(result.running_event, threading.Event)
    assert isinstance(result.processor, threading.Thread)


def test_dispatcher_running(mock_app_group_name):
    dispatcher = Dispatcher(group=mock_app_group_name)
    dispatcher.start()

    result = dispatcher.running

    assert result is True
    dispatcher.stop()
    dispatcher.executor.shutdown()


def test_dispatcher_stop(mock_app_group_name):
    dispatcher = Dispatcher(group=mock_app_group_name)
    dispatcher.start()
    dispatcher.stop()

    result = dispatcher.running

    assert result is False
    dispatcher.executor.shutdown()


def test_dispatcher_dispatch_event(mock_app_group_name):
    test_event = Event("evt-id", "orders", {"id": "ORD-1111-1111-1111"})
    dispatcher = Dispatcher(group=mock_app_group_name)
    dispatcher.start()
    dispatcher.dispatch_event(test_event)
    dispatcher.stop()
    dispatcher.executor.shutdown()
