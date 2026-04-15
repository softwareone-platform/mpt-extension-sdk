import pytest
from mpt_api_client.models.model import ModelList

from mpt_extension_sdk.models.parameter import ParameterBag, ParameterValue


class FakeSerializableValue:
    def __init__(self, payload):
        self.payload = payload

    def to_dict(self):
        return self.payload


def test_parameter_value_normalizes_nested_values():
    result = ParameterValue.model_validate({
        "externalId": "param-1",
        "value": {
            "item": FakeSerializableValue({"nested": "value"}),
            "list": ModelList([FakeSerializableValue({"deep": 1})]),
        },
    })

    assert result.value == {
        "item": {"nested": "value"},
        "list": [{"deep": 1}],
    }


def test_parameter_value_serializes_value():
    parameter = ParameterValue(
        external_id="param-1",
        value={
            "item": FakeSerializableValue({"nested": "value"}),
            "list": [FakeSerializableValue({"deep": 1})],
        },
    )

    result = parameter.model_dump(by_alias=True)

    assert result["value"] == {
        "item": {"nested": "value"},
        "list": [{"deep": 1}],
    }


@pytest.fixture
def parameter_bag():
    return ParameterBag(
        ordering=[
            ParameterValue(external_id="ord-1", value="one"),
            ParameterValue(external_id="shared", value="ordering"),
        ],
        fulfillment=[
            ParameterValue(external_id="ful-1", value="two"),
            ParameterValue(external_id="shared", value="fulfillment"),
        ],
    )


def test_get_parameter_reads_from_phase(parameter_bag):
    result = (
        parameter_bag.get_parameter("ord-1", "ordering"),
        parameter_bag.get_parameter("ful-1", "fulfillment"),
        parameter_bag.get_parameter("missing", "ordering"),
    )

    assert result == (
        parameter_bag.ordering[0],
        parameter_bag.fulfillment[0],
        None,
    )


def test_get_phase_parameter_raises_when_missing(parameter_bag):
    with pytest.raises(ValueError, match="No fulfillment parameter found"):
        parameter_bag.get_fulfillment_parameter("missing")

    with pytest.raises(ValueError, match="No ordering parameter found"):
        parameter_bag.get_ordering_parameter("missing")


def test_get_phase_values(parameter_bag):
    result = (
        parameter_bag.get_ordering_value("ord-1"),
        parameter_bag.get_fulfillment_value("ful-1"),
        parameter_bag.get_ordering_value("missing"),
    )

    assert result == ("one", "two", None)


def test_with_ordering_value_updates_param(parameter_bag):
    result = parameter_bag.with_ordering_value("ord-1", "updated")

    assert result.ordering[0].value == "updated"
    assert parameter_bag.ordering[0].value == "one"


def test_with_ordering_value_appends_param(parameter_bag):
    result = parameter_bag.with_ordering_value("new-param", 3)

    assert result.ordering[-1].external_id == "new-param"
    assert result.ordering[-1].value == 3


def test_with_fulfillment_error_updates_param(parameter_bag):
    result = parameter_bag.with_fulfillment_error("ful-1", {"message": "boom"})

    assert result.fulfillment[0].error == {"message": "boom"}
    assert result.fulfillment[0].constraints.hidden is False
    assert result.fulfillment[0].constraints.required is True


def test_with_ordering_error_appends_param(parameter_bag):
    result = parameter_bag.with_ordering_error("new-param", {"message": "boom"})

    assert result.ordering[-1].external_id == "new-param"
    assert result.ordering[-1].error == {"message": "boom"}
    assert result.ordering[-1].constraints.hidden is False
    assert result.ordering[-1].constraints.required is True


def test_with_visibility_updates_both_phases(parameter_bag):
    result = parameter_bag.with_visibility(["ord-1", "shared"])

    assert [parameter.constraints.hidden for parameter in result.ordering] == [False, False]
    assert [parameter.constraints.hidden for parameter in result.fulfillment] == [True, False]
