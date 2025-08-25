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
    """Callback for when a future is done."""
    del futures[key]
    exc = future.exception()
    if not exc:
        logger.debug("Future for %s has been completed successfully", key)
        return
    logger.error("Future for %s has failed: %s", key, exc)


class Dispatcher:
    """Event dispatcher."""
    def __init__(self, group=DEFAULT_APP_CONFIG_GROUP, name=DEFAULT_APP_CONFIG_NAME):
        self.registry: EventsRegistry = get_events_registry(group=group, name=name)
        self.queue = deque()
        self.futures = {}
        self.executor = ThreadPoolExecutor()
        self.running_event = threading.Event()
        self.processor = threading.Thread(target=self.process_events)
        self.client = setup_client()

    def start(self):
        """Start the dispatcher."""
        self.running_event.set()
        self.processor.start()

    def stop(self):
        """Stop the dispatcher."""
        self.running_event.clear()
        self.processor.join()

    @property
    def running(self):
        """Return True if the dispatcher is running."""
        return self.running_event.is_set()

    def dispatch_event(self, event: Event):  # pragma: no cover
        """Dispatch an event to the appropriate listener."""
        if self.registry.is_event_supported(event.type):
            logger.info("event of type %s with id %s accepted", event.type, event.id)
            self.queue.appendleft((event.type, event))

    def process_events(self):  # pragma: no cover
        """Process events from the queue."""
        while self.running:
            skipped = []
            while len(self.queue) > 0:
                event_type, event = self.queue.pop()
                logger.debug(
                    "got event of type %s (%s) from queue...", event_type, event.id
                )
                listener = wrap_for_trace(
                    self.registry.get_listener(event_type), event_type
                )
                if (event.type, event.id) in self.futures:
                    logger.info(
                        "An event for (%s, %s) is already processing, skip it",
                        event.type, event.id
                    )
                    skipped.append((event.type, event))
                else:
                    future = self.executor.submit(listener, self.client, event)
                    self.futures[event.type, event.id] = future
                    future.add_done_callback(
                        functools.partial(
                            done_callback, self.futures, (event.type, event.id)
                        )
                    )

            self.queue.extendleft(skipped)
            time.sleep(0.5)
