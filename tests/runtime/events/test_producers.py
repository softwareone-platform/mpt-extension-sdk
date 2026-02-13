from urllib.parse import urljoin

import pytest

from mpt_extension_sdk.flows.context import Context
from mpt_extension_sdk.runtime.events.dispatcher import Dispatcher
from mpt_extension_sdk.runtime.events.producers import OrderEventProducer


@pytest.fixture(autouse=True)
def mock_time_sleep(mocker):
    mocker.patch("mpt_extension_sdk.runtime.events.producers.time.sleep", autospec=True)


def test_event_producer_get_processing_orders_invalid_response(
    mpt_client,
    mock_wrap_event,
    requests_mocker,
    mock_settings_product_ids,
    mock_generic_response_error,
    mock_app_group_name,
    caplog,
):
    limit = 10
    offset = 0
    rql_query = (
        f"and(in(agreement.product.id,({mock_settings_product_ids})),eq(status,'processing'))"
    )
    url = (
        f"commerce/orders?{rql_query}"
        "&select=audit,parameters,lines,subscriptions,subscriptions.lines,agreement,buyer,seller,"
        "authorization.externalIds&order=audit.created.at"
        f"&limit={limit}&offset={offset}"
    )
    requests_mocker.get(
        urljoin(mpt_client.base_url, url),
        status=400,
        json=mock_generic_response_error,
    )
    dispatcher = Dispatcher(group=mock_app_group_name)
    dispatcher.start()
    dispatcher.dispatch_event(mock_wrap_event)

    result = OrderEventProducer(dispatcher).get_processing_orders()

    assert len(result) == 0
    dispatcher.stop()
    dispatcher.executor.shutdown()


def test_event_producers_has_more_pages(
    mock_meta_with_pagination_has_more_pages, mock_app_group_name
):
    dispatcher = Dispatcher(group=mock_app_group_name)

    result = OrderEventProducer(dispatcher).has_more_pages(mock_meta_with_pagination_has_more_pages)

    assert result is True


def test_event_producers_has_no_more_pages(
    mock_wrap_event, mock_meta_with_pagination_has_no_more_pages, mock_app_group_name
):
    dispatcher = Dispatcher(group=mock_app_group_name)
    dispatcher.start()
    dispatcher.dispatch_event(mock_wrap_event)

    result = OrderEventProducer(dispatcher).has_more_pages(
        mock_meta_with_pagination_has_no_more_pages
    )

    assert result is False
    dispatcher.stop()
    dispatcher.executor.shutdown()


def test_event_producer_start(mock_app_group_name):
    dispatcher = Dispatcher(group=mock_app_group_name)
    dispatcher.start()
    order_event_producer = OrderEventProducer(dispatcher)
    order_event_producer.start()

    result = order_event_producer.running

    assert result is True
    order_event_producer.stop()
    dispatcher.stop()
    dispatcher.executor.shutdown()


def test_event_producer_stop(mock_app_group_name):
    dispatcher = Dispatcher(group=mock_app_group_name)
    dispatcher.start()
    order_event_producer = OrderEventProducer(dispatcher)
    order_event_producer.start()
    order_event_producer.stop()

    result = order_event_producer.running

    dispatcher.stop()
    dispatcher.executor.shutdown()
    assert result is False


def test_event_producer_sleep(mock_app_group_name):
    dispatcher = Dispatcher(group=mock_app_group_name)
    dispatcher.start()
    order_event_producer = OrderEventProducer(dispatcher)
    order_event_producer.start()
    order_event_producer.sleep(2, 0.5)

    result = order_event_producer.running

    assert result is True
    order_event_producer.stop()
    dispatcher.stop()
    dispatcher.executor.shutdown()


def test_produce_events_context(mocker, mock_app_group_name, order_factory, settings):
    order_1 = order_factory(order_id="ORD-1111-1111")
    order_2 = order_factory(order_id="ORD-2222-2222")
    mock_orders = [order_1, order_2]
    mock_contexts = [
        mocker.Mock(order_id=order_1["id"], spec=Context),
        mocker.Mock(order_id=order_2["id"], spec=Context),
    ]
    setup_contexts_func = mocker.Mock(return_value=mock_contexts)
    mock_import_string = mocker.patch(
        "mpt_extension_sdk.runtime.events.producers.import_string",
        return_value=setup_contexts_func,
        autospec=True,
    )
    dispatcher = Dispatcher(group=mock_app_group_name)
    producer = OrderEventProducer(dispatcher)
    producer.running_event.set()
    producer.get_processing_orders = mocker.Mock(return_value=mock_orders, spec=True)
    producer.sleep = mocker.MagicMock(spec=True)
    mocker.patch.object(dispatcher, "dispatch_event")
    mocker.patch.object(producer.running_event, "is_set", side_effect=[True, False])

    producer.produce_events()  # act

    called_events = [call.args[0] for call in dispatcher.dispatch_event.call_args_list]
    mock_import_string.assert_called_once_with(settings.MPT_SETUP_CONTEXTS_FUNC)
    setup_contexts_func.assert_called_once_with(producer.client, mock_orders)
    assert producer.get_processing_orders.call_count == 1
    assert dispatcher.dispatch_event.call_count == len(mock_contexts)
    for i, ctx in enumerate(mock_contexts):
        event = called_events[i]
        assert event.id == ctx.order_id
        assert event.type == "orders"
        assert event.data == ctx
