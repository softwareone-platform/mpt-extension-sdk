from urllib.parse import urljoin

from mpt_extension_sdk.runtime.events.dispatcher import Dispatcher
from mpt_extension_sdk.runtime.events.producers import OrderEventProducer


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


def test_produce_events_context(mocker, mock_app_group_name, order_factory, settings):
    """Test produce_events dispatches context events when DISPATCHER_TYPE is CONTEXT."""
    order_1 = order_factory(order_id="ORD-1111-1111")
    order_2 = order_factory(order_id="ORD-2222-2222")

    mock_orders = [order_1, order_2]

    mock_contexts = [
        mocker.MagicMock(order_id=order_1["id"], autospec=True),
        mocker.MagicMock(order_id=order_2["id"], autospec=True),
    ]

    mock_import_string = mocker.patch("mpt_extension_sdk.runtime.events.producers.import_string")

    setup_contexts_func = mocker.Mock(return_value=mock_contexts)

    mock_import_string.return_value = setup_contexts_func

    dispatcher = Dispatcher(group=mock_app_group_name)
    producer = OrderEventProducer(dispatcher)
    producer.running_event.set()

    producer.get_processing_orders = mocker.MagicMock(return_value=mock_orders, autospec=True)
    producer.sleep = mocker.MagicMock(autospec=True)

    mocker.patch.object(dispatcher, "dispatch_event")
    mocker.patch.object(producer.running_event, "is_set", side_effect=[True, False])

    producer.produce_events()

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
