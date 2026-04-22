import json

from mpt_extension_sdk.runtime.bootstrap.identity import load_identity, save_identity


def test_load_identity_for_missing_file(tmp_path):
    result = load_identity(tmp_path / "missing.json")

    assert result == {}


def test_load_identity_for_invalid_json(tmp_path):
    path = tmp_path / "identity.json"
    path.write_text("{not-json", encoding="utf-8")

    result = load_identity(path)

    assert result == {}


def test_load_identity_for_non_mapping_json(tmp_path):
    path = tmp_path / "identity.json"
    path.write_text('["not", "a", "mapping"]', encoding="utf-8")

    result = load_identity(path)

    assert result == {}


def test_load_identity_mapping_payload(tmp_path):
    path = tmp_path / "identity.json"
    path.write_text(json.dumps({"mrok": {"extension": "EXT-1"}}), encoding="utf-8")

    result = load_identity(path)

    assert result == {"mrok": {"extension": "EXT-1"}}


def test_save_identity_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "identity.json"
    save_identity(path, {"channel": "ok"})

    result = json.loads(path.read_text(encoding="utf-8"))

    assert result == {"channel": "ok"}
