import datetime as dt
import logging
from dataclasses import dataclass
from pathlib import Path

import pytest

from mpt_extension_sdk import EventRouter
from mpt_extension_sdk.api.models.events import Event, TaskEvent
from mpt_extension_sdk.models.agreement import Agreement
from mpt_extension_sdk.models.order import Order
from mpt_extension_sdk.runtime.models import MetaConfig, MetaEvent
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.settings.runtime import RuntimeSettings


@pytest.fixture
def logger():
    return logging.getLogger("tests")


@pytest.fixture
def order_factory():
    def factory(order_id="ORD-1111-1112"):
        return Order.model_construct(id=order_id)

    return factory


@pytest.fixture
def agreement_factory():
    def factory(agreement_id="AGR-1111-1112"):
        return Agreement.model_construct(id=agreement_id)

    return factory


@pytest.fixture
def event_factory():
    def factory(object_type="Order", object_id="ORD-1111-1112", event_id="EVT-1111-1112"):
        return Event.model_validate({
            "id": event_id,
            "details": {
                "enqueue_time": dt.datetime(2024, 1, 1, 12, 0, tzinfo=dt.UTC),
                "event_type": "OrderPurchased",
                "delivery_time": dt.datetime(2024, 1, 1, 12, 1, tzinfo=dt.UTC),
            },
            "object": {
                "id": object_id,
                "object_type": object_type,
                "name": f"{object_type}Name",
            },
        })

    return factory


@pytest.fixture
def task_event_factory(event_factory):
    def factory(object_type="Order", task_id="TASK-1111-1112"):
        event = event_factory(object_type=object_type)
        payload = event.model_dump(by_alias=False)
        payload["task"] = {"id": task_id}
        return TaskEvent.model_validate(payload)

    return factory


@pytest.fixture
def meta_config():
    return MetaConfig(
        version="1.0.0",
        openapi="/bypass/openapi.json",
        events=[
            MetaEvent(
                event="OrderPurchased",
                condition=None,
                path="/events/orders/purchase",
                task=False,
            )
        ],
    )


@pytest.fixture
def runtime_settings(meta_config):
    return RuntimeSettings(
        app_module="mock_app.app",
        settings_module="mock_app.settings",
        ext_api_key="extension-api-key",
        base_url="https://extensions.example.com",
        extension_id="EXT-1",
        mpt_api_base_url="https://api.example.com",
        mpt_api_token="mpt-token",
        external_id="external-id",
        identity_file_path=Path("/tmp/external-id_identity.json"),
        meta_config=meta_config,
        meta_file_path=Path("/tmp/meta.yaml"),
        local_host="0.0.0.0",
        local_port=8080,
        local_reload=True,
        local_workers=1,
        log_level="INFO",
        observability_enabled=False,
        applicationinsights_connection_string="",
        otel_service_name="tests",
        ziti_workers=4,
        ziti_reload=False,
    )


@pytest.fixture
def dummy_handler():
    def wrapper(event, context):
        return event

    return wrapper


@pytest.fixture
def extension_router():
    return EventRouter(prefix="/events/orders")


@pytest.fixture
def fake_api_service_factory(mocker):
    def factory(fake_service=None):
        if fake_service is None:
            fake_service = mocker.AsyncMock(spec=MPTAPIService)

        @dataclass
        class FakeAPIService:  # noqa: WPS431
            @classmethod
            def from_config(cls, base_url, api_token):
                return fake_service

        return FakeAPIService

    return factory
