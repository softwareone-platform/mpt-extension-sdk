import functools
import logging
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from mpt_extension_sdk.constants import (
    DEFAULT_APP_CONFIG_GROUP,
    DEFAULT_APP_CONFIG_NAME,
)
from mpt_extension_sdk.core.events.dataclasses import Event
from mpt_extension_sdk.core.events.registry import EventsRegistry
from mpt_extension_sdk.core.utils import setup_client
from mpt_extension_sdk.runtime.events.utils import wrap_for_trace
from mpt_extension_sdk.runtime.utils import get_events_registry

logger = logging.getLogger(__name__)


def done_callback(futures, key, future):  # pragma: no cover
    del futures[key]
    exc = future.exception()
    if not exc:
        logger.debug(f"Future for {key} has been completed successfully")
        return
    logger.error(f"Future for {key} has failed: {exc}")


class Dispatcher:
    def __init__(self, group=DEFAULT_APP_CONFIG_GROUP, name=DEFAULT_APP_CONFIG_NAME):
        self.registry: EventsRegistry = get_events_registry(group=group, name=name)
        self.queue = deque()
        self.futures = {}
        self.executor = ThreadPoolExecutor()
        self.running_event = threading.Event()
        self.processor = threading.Thread(target=self.process_events)
        self.client = setup_client()

    def start(self):
        self.running_event.set()
        self.processor.start()

    def stop(self):
        self.running_event.clear()
        self.processor.join()

    @property
    def running(self):
        return self.running_event.is_set()

    def dispatch_event(self, event: Event):  # pragma: no cover
        if self.registry.is_event_supported(event.type):
            logger.info(f"event of type {event.type} with id {event.id} accepted")
            self.queue.appendleft((event.type, event))

    def process_events(self):  # pragma: no cover
        while self.running:
            skipped = []
            while len(self.queue) > 0:
                event_type, event = self.queue.pop()
                logger.debug(
                    f"got event of type {event_type} ({event.id}) from queue..."
                )
                listener = wrap_for_trace(
                    self.registry.get_listener(event_type), event_type
                )
                if (event.type, event.id) not in self.futures:
                    future = self.executor.submit(listener, self.client, event)
                    self.futures[(event.type, event.id)] = future
                    future.add_done_callback(
                        functools.partial(
                            done_callback, self.futures, (event.type, event.id)
                        )
                    )
                else:
                    logger.info(
                        f"An event for {(event.type, event.id)} is already processing, skip it"
                    )
                    skipped.append((event.type, event))

            self.queue.extendleft(skipped)
            time.sleep(0.5)
