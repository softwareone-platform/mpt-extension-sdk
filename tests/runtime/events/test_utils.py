from mpt_extension_sdk.runtime.events.utils import setup_contexts


def test_setup_contexts(mpt_client, order_factory):
    """Test setup_contexts function with a single order."""
    orders = [order_factory()]
    contexts = setup_contexts(mpt_client, orders)
    assert len(contexts) == 1
    assert contexts[0].order == orders[0]
