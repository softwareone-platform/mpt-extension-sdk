import logging
import threading
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager

import requests
from django.conf import settings

from mpt_extension_sdk.core.events.dataclasses import Event
from mpt_extension_sdk.core.utils import setup_client
from mpt_extension_sdk.swo_rql import RQLQuery

logger = logging.getLogger(__name__)


class EventProducer(ABC):
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.running_event = threading.Event()
        self.producer = threading.Thread(target=self.produce_events)

    @property
    def running(self):
        return self.running_event.is_set()

    def start(self):
        self.running_event.set()
        self.producer.start()

    def stop(self):
        self.running_event.clear()
        self.producer.join()

    @contextmanager
    def sleep(self, secs, interval=0.5):  # pragma: no cover
        yield
        sleeped = 0
        while sleeped < secs and self.running_event.is_set():
            time.sleep(interval)
            sleeped += interval

    @abstractmethod
    def produce_events(self):
        pass

    @abstractmethod
    def produce_events_with_context(self):
        pass


class OrderEventProducer(EventProducer):
    def __init__(self, dispatcher):
        super().__init__(dispatcher)
        self.client = setup_client()

    def produce_events(self):
        while self.running:
            with self.sleep(settings.MPT_ORDERS_API_POLLING_INTERVAL_SECS):
                orders = self.get_processing_orders()
                logger.info(f"{len(orders)} orders found for processing...")
                for order in orders:
                    self.dispatcher.dispatch_event(Event(order["id"], "orders", order))

    def produce_events_with_context(self):  # pragma: no cover
        while self.running:
            with self.sleep(settings.MPT_ORDERS_API_POLLING_INTERVAL_SECS):
                orders = self.get_processing_orders()
                orders, contexts = self.filter_and_enrich(self.client, orders)
                logger.info(f"{len(orders)} orders found for processing...")
                for order, context in zip(orders, contexts, strict=False):
                    self.dispatcher.dispatch_event(
                        Event(order["id"], "orders", order, context)
                    )

    def get_processing_orders(self):
        orders = []
        rql_query = RQLQuery().agreement.product.id.in_(
            settings.MPT_PRODUCTS_IDS
        ) & RQLQuery(status="processing")
        url = (
            f"/commerce/orders?{rql_query}&select=audit,parameters,lines,subscriptions,"
            f"subscriptions.lines,agreement,buyer,seller&order=audit.created.at"
        )
        page = None
        limit = 10
        offset = 0
        while self.has_more_pages(page):
            try:
                response = self.client.get(f"{url}&limit={limit}&offset={offset}")
            except requests.RequestException:
                logger.exception("Cannot retrieve orders")
                return []
            if response.status_code == 200:
                page = response.json()
                orders.extend(page["data"])
            else:
                logger.warning(
                    f"Order API error: {response.status_code} {response.content}"
                )
                return []
            offset += limit

        return orders

    def has_more_pages(self, orders):
        if not orders:
            return True
        pagination = orders["$meta"]["pagination"]
        return pagination["total"] > pagination["limit"] + pagination["offset"]
