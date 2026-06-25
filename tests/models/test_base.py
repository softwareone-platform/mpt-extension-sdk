import datetime as dt

import pytest
from pydantic import Field, ValidationError

from mpt_extension_sdk.models.base import BaseModel


class Nested(BaseModel):
    amount: int = Field(serialization_alias="nestedValue", validation_alias="nestedValue")


class Sample(BaseModel):
    id: str
    display_name: str | None = Field(
        default=None, serialization_alias="displayName", validation_alias="displayName"
    )
    settings: dict = Field(default_factory=dict)
    created: dt.datetime | None = None
    nested: Nested | None = None


class ModelWithToDict:
    """Stub mimicking an mpt_api_client model: exposes ``to_dict``."""

    def __init__(self, payload):
        self._payload = payload

    def to_dict(self):
        return self._payload


def test_to_dict_uses_aliases():
    sample = Sample(id="1", display_name="Foo", nested=Nested(amount=5))

    result = sample.to_dict()

    assert result["displayName"] == "Foo"
    assert result["nested"] == {"nestedValue": 5}


def test_to_dict_excludes_none():
    sample = Sample(id="1")

    result = sample.to_dict()

    assert result == {"id": "1", "settings": {}}


def test_to_dict_serializes_in_json_mode():
    created = dt.datetime(2026, 6, 22, 9, 0, tzinfo=dt.UTC)
    sample = Sample(id="1", created=created)

    result = sample.to_dict()

    assert result["created"] == "2026-06-22T09:00:00Z"


def test_from_payload_accepts_alias_keys():
    payload = {"id": "1", "displayName": "Foo"}

    result = Sample.from_payload(payload)

    assert result.display_name == "Foo"


def test_from_payload_accepts_name_keys():
    payload = {"id": "1", "display_name": "Foo"}

    result = Sample.from_payload(payload)

    assert result.display_name == "Foo"


def test_from_payload_normalizes_objects():
    payload = ModelWithToDict({"id": "1", "displayName": "Foo", "settings": {"paid": False}})

    result = Sample.from_payload(payload)

    assert result.settings == {"paid": False}


def test_from_payload_keeps_plain_dicts():
    payload = {"id": "1", "settings": {"k": "v"}}

    result = Sample.from_payload(payload)

    assert result.settings == {"k": "v"}


def test_from_payload_roundtrips():
    nested = Nested(amount=5)
    original = Sample(id="1", display_name="Foo", settings={"a": 1}, nested=nested)

    result = Sample.from_payload(original.to_dict())

    assert result == original


def test_extra_keys_are_preserved():
    payload = {"id": "1", "unknownKey": 123}

    result = Sample.from_payload(payload)

    assert result.model_extra == {"unknownKey": 123}


def test_instances_are_frozen():
    sample = Sample(id="1")

    with pytest.raises(ValidationError):
        sample.id = "2"
