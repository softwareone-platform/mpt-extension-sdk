import pytest

from mpt_extension_sdk.api.results import TaskResult


def test_reference_keeps_relative_uri():
    result = TaskResult.reference("/public/v1/commerce/agreements/AGR-1")

    assert result.uri == "/public/v1/commerce/agreements/AGR-1"


@pytest.mark.parametrize(
    "uri",
    [
        "https://api.example.com/public/v1/commerce/agreements/AGR-1",
        "public/v1/commerce/agreements/AGR-1",
        "",
    ],
)
def test_reference_rejects_non_relative_uri(uri):
    with pytest.raises(ValueError, match="relative URI"):
        TaskResult.reference(uri)


def test_init_rejects_non_relative_uri():
    with pytest.raises(ValueError, match="relative URI"):
        TaskResult(uri="https://api.example.com/public/v1/commerce/agreements/AGR-1")
