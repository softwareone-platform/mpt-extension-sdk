import pytest
from pydantic import BaseModel, Field, ValidationError

from mpt_extension_sdk.api.error_mapping import PydanticValidationErrorMapper


class Payload(BaseModel):
    """Payload model used to produce pydantic validation errors."""

    amount: int = Field(gt=0)


@pytest.fixture
def validation_error():
    try:
        Payload.model_validate({"amount": 0})
    except ValidationError as error:
        return error

    pytest.fail("Expected payload validation to fail")


def test_pydantic_error_mapper_maps(validation_error):
    result = PydanticValidationErrorMapper.map(validation_error)

    assert len(result) == 1
    assert result[0].pointer == "#/amount"
    assert result[0].detail == "Input should be greater than 0"


def test_pydantic_error_mapper_maps_root_pointer():
    result = PydanticValidationErrorMapper.map_pointer(("body",))

    assert result == "#"
