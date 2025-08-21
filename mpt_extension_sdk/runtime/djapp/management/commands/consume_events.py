import signal  # pragma: no cover
from threading import Event  # pragma: no cover
from typing import ClassVar  # pragma: no cover

from django.core.management.base import BaseCommand  # pragma: no cover

from mpt_extension_sdk.constants import CONSUME_EVENTS_HELP_TEXT  # pragma: no cover
from mpt_extension_sdk.runtime.events.dispatcher import Dispatcher  # pragma: no cover
from mpt_extension_sdk.runtime.events.producers import (
    OrderEventProducer,  # pragma: no cover
)


class Command(BaseCommand):  # pragma: no cover
    """Command to consume events."""
    help = CONSUME_EVENTS_HELP_TEXT
    producer_classes: ClassVar[list] = [
        OrderEventProducer,
    ]
    producers: ClassVar[list] = []

    def handle(self, *args, **options):
        """Handle the command."""
        self.shutdown_event = Event()
        self.dispatcher = Dispatcher()
        self.dispatcher.start()

        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)
        for producer_cls in self.producer_classes:
            producer = producer_cls(self.dispatcher)
            self.producers.append(producer)
            producer.start()

        self.shutdown_event.wait()
        for producer in self.producers:
            producer.stop()
        self.dispatcher.stop()

    def shutdown(self, signum, frame):
        """Shutdown the command."""
        self.shutdown_event.set()
