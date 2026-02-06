from mpt_extension_sdk.runtime.logging import ReprHighlighter


def test_repr_highlighter(
    mock_logging_account_prefixes,
    mock_logging_catalog_prefixes,
    mock_logging_commerce_prefixes,
    mock_logging_aux_prefixes,
    mock_logging_all_prefixes,
    mock_highlights,
):
    result = ReprHighlighter()

    assert result.accounts_prefixes == mock_logging_account_prefixes
    assert result.catalog_prefixes == mock_logging_catalog_prefixes
    assert result.commerce_prefixes == mock_logging_commerce_prefixes
    assert result.aux_prefixes == mock_logging_aux_prefixes
    assert result.all_prefixes == mock_logging_all_prefixes
    assert result.highlights == mock_highlights
