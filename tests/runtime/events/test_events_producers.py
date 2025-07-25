from urllib.parse import urljoin

from mpt_extension_sdk.runtime.events.dispatcher import Dispatcher
from mpt_extension_sdk.runtime.events.producers import (
    OrderEventProducer,
)


def test_event_producer_get_processing_orders(
    mpt_client,
    mock_wrap_event,
    requests_mocker,
    mock_settings_product_ids,
    mock_get_order_for_producer,
    mock_app_group_name,
):
    limit = 10
    offset = 0
    rql_query = f"and(in(agreement.product.id,({mock_settings_product_ids})),eq(status,processing))"
    url = (
        f"/v1/commerce/orders?{rql_query}"
        "&select=audit,parameters,lines,subscriptions,subscriptions.lines,agreement,buyer,seller&order=audit.created.at"
        f"&limit={limit}&offset={offset}"
    )
    requests_mocker.get(
        urljoin(mpt_client.base_url, url),
        json=mock_get_order_for_producer,
    )

    dispatcher = Dispatcher(group=mock_app_group_name)
    dispatcher.start()
    dispatcher.dispatch_event(mock_wrap_event)

    orders = OrderEventProducer(dispatcher).get_processing_orders()
    dispatcher.stop()

    dispatcher.executor.shutdown()

    assert len(orders) == 1


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
    rql_query = f"and(in(agreement.product.id,({mock_settings_product_ids})),eq(status,processing))"
    url = (
        f"/v1/commerce/orders?{rql_query}"
        "&select=audit,parameters,lines,subscriptions,subscriptions.lines,agreement,buyer,seller&order=audit.created.at"
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

    orders = OrderEventProducer(dispatcher).get_processing_orders()
    dispatcher.stop()

    dispatcher.executor.shutdown()

    assert len(orders) == 0


def test_event_producers_has_more_pages(
    mock_wrap_event,
    mock_meta_with_pagination_has_more_pages,
    mock_app_group_name,
):
    dispatcher = Dispatcher(group=mock_app_group_name)
    dispatcher.start()
    dispatcher.dispatch_event(mock_wrap_event)

    has_more_pages = OrderEventProducer(dispatcher).has_more_pages(
        mock_meta_with_pagination_has_more_pages
    )
    dispatcher.stop()
    dispatcher.executor.shutdown()
    assert has_more_pages is True


def test_event_producers_has_no_more_pages(
    mock_wrap_event,
    mock_meta_with_pagination_has_no_more_pages,
    mock_app_group_name,
):
    dispatcher = Dispatcher(group=mock_app_group_name)
    dispatcher.start()
    dispatcher.dispatch_event(mock_wrap_event)

    has_more_pages = OrderEventProducer(dispatcher).has_more_pages(
        mock_meta_with_pagination_has_no_more_pages
    )
    dispatcher.stop()
    dispatcher.executor.shutdown()
    assert has_more_pages is False


def test_event_producer_start(mock_app_group_name):
    dispatcher = Dispatcher(group=mock_app_group_name)
    dispatcher.start()
    order_event_producer = OrderEventProducer(dispatcher)
    order_event_producer.start()
    is_running = order_event_producer.running
    order_event_producer.stop()
    dispatcher.stop()
    dispatcher.executor.shutdown()
    assert is_running


def test_event_producer_stop(mock_app_group_name):
    dispatcher = Dispatcher(group=mock_app_group_name)
    dispatcher.start()
    order_event_producer = OrderEventProducer(dispatcher)
    order_event_producer.start()
    order_event_producer.stop()
    is_running = order_event_producer.running
    dispatcher.stop()
    dispatcher.executor.shutdown()
    assert not is_running


def test_event_producer_sleep(mock_app_group_name):
    dispatcher = Dispatcher(group=mock_app_group_name)
    dispatcher.start()
    order_event_producer = OrderEventProducer(dispatcher)
    order_event_producer.start()
    order_event_producer.sleep(2, 0.5)
    is_running = order_event_producer.running
    order_event_producer.stop()
    dispatcher.stop()
    dispatcher.executor.shutdown()
    assert is_running
