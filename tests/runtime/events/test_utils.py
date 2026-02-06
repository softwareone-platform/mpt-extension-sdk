from mpt_extension_sdk.runtime.events.utils import setup_contexts


def test_setup_contexts(mpt_client, order):
    orders = [order]

    result = setup_contexts(mpt_client, orders)

    assert len(result) == 1
    assert result[0].order == orders[0]
