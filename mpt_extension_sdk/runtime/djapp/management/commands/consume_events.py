import signal
from threading import Event

from django.core.management.base import BaseCommand

from mpt_extension_sdk.constants import CONSUME_EVENTS_HELP_TEXT
from mpt_extension_sdk.runtime.events.dispatcher import Dispatcher
from mpt_extension_sdk.runtime.events.producers import OrderEventProducer


class Command(BaseCommand):  # pragma: no cover
    help = CONSUME_EVENTS_HELP_TEXT
    producer_classes = [
        OrderEventProducer,
    ]
    producers = []

    def handle(self, *args, **options):
        self.shutdown_event = Event()
        self.dispatcher = Dispatcher()
        self.dispatcher.start()

        def shutdown(signum, frame):
            self.shutdown_event.set()

        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)
        for producer_cls in self.producer_classes:
            producer = producer_cls(self.dispatcher)
            self.producers.append(producer)
            producer.start()

        self.shutdown_event.wait()
        for producer in self.producers:
            producer.stop()
        self.dispatcher.stop()
