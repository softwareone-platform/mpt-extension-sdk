import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from mpt_extension_sdk.core.events.dataclasses import Event
from mpt_extension_sdk.mpt_http.base import MPTClient
from mpt_extension_sdk.runtime.events.dispatcher import Dispatcher


def test_dispatcher():
    dispatcher = Dispatcher()
    assert dispatcher is not None
    assert isinstance(dispatcher.client, MPTClient)
    assert isinstance(dispatcher.executor, ThreadPoolExecutor)
    assert isinstance(dispatcher.queue, deque)
    assert dispatcher.futures == {}
    assert isinstance(dispatcher.running_event, threading.Event)
    assert isinstance(dispatcher.processor, threading.Thread)


def test_dispatcher_running():
    dispatcher = Dispatcher()
    dispatcher.start()
    is_running = dispatcher.running
    dispatcher.stop()
    dispatcher.executor.shutdown()
    assert is_running


def test_dispatcher_stop():
    dispatcher = Dispatcher()
    dispatcher.start()
    dispatcher.stop()
    is_running = dispatcher.running
    dispatcher.executor.shutdown()
    assert not is_running


def test_dispatcher_dispatch_event():
    test_event = Event("evt-id", "orders", {"id": "ORD-1111-1111-1111"})
    dispatcher = Dispatcher()
    dispatcher.start()
    dispatcher.dispatch_event(test_event)
    dispatcher.stop()
    dispatcher.executor.shutdown()
