from pathlib import Path

import pytest
import yaml

from mpt_extension_sdk.errors.runtime import ConfigError
from mpt_extension_sdk.runtime.models import MetaConfig, MetaPlug


@pytest.fixture
def metadata_path(tmp_path):
    return tmp_path / "meta.yaml"


def test_meta_config_from_file_reads_yaml(meta_config, metadata_path):
    metadata_path.write_text(
        yaml.safe_dump(meta_config.model_dump(exclude_none=True, by_alias=True), sort_keys=False),
        encoding="utf-8",
    )

    result = MetaConfig.from_file(metadata_path)

    assert result == meta_config


def test_from_file_rejects_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="Metadata file was not found"):
        MetaConfig.from_file(tmp_path / "missing.yaml")


def test_from_file_rejects_non_mapping_root(metadata_path):
    metadata_path.write_text(yaml.safe_dump(["bad-root"]), encoding="utf-8")

    with pytest.raises(ConfigError, match="Metadata root must be a mapping"):
        MetaConfig.from_file(metadata_path)


def test_from_file_rejects_invalid_schema(metadata_path):
    metadata_path.write_text(
        yaml.safe_dump({"version": "1.0.0", "openapi": "/openapi.json", "events": [{}]}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="Invalid metadata schema"):
        MetaConfig.from_file(metadata_path)


def test_meta_config_to_file_writes_yaml(meta_config, metadata_path):
    meta_config.to_file(metadata_path)  # act

    assert Path(metadata_path).read_text(encoding="utf-8") == yaml.safe_dump(
        meta_config.model_dump(exclude_none=True, by_alias=True),
        sort_keys=False,
        allow_unicode=False,
    )


def test_meta_config_supports_plugs(metadata_path):
    metadata_path.write_text(
        yaml.safe_dump(
            {
                "openapi": "/bypass/openapi.json",
                "version": "1.0.0",
                "events": [],
                "plugs": [
                    {
                        "id": "adobe",
                        "name": "Adobe",
                        "description": "Adobe widget",
                        "icon": "/static/adobe.png",
                        "socket": "commerce.agreements.agreement",
                        "href": "/static/main-menu.js",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = MetaConfig.from_file(metadata_path)

    assert result.plugs == [
        MetaPlug(
            id="adobe",
            name="Adobe",
            description="Adobe widget",
            icon="/static/adobe.png",
            socket="commerce.agreements.agreement",
            href="/static/main-menu.js",
        )
    ]


def test_meta_config_supports_container_plugs(metadata_path):
    metadata_path.write_text(
        yaml.safe_dump(
            {
                "openapi": "/bypass/openapi.json",
                "version": "1.0.0",
                "events": [],
                "plugs": [
                    {
                        "id": "learn-extensions",
                        "name": "Learn Extensions",
                        "socket": "portal",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = MetaConfig.from_file(metadata_path)

    assert result.plugs == [
        MetaPlug(id="learn-extensions", name="Learn Extensions", socket="portal")
    ]


def test_meta_config_supports_socketless_plugs(metadata_path):
    metadata_path.write_text(
        yaml.safe_dump(
            {
                "openapi": "/bypass/openapi.json",
                "version": "1.0.0",
                "events": [],
                "plugs": [
                    {
                        "id": "confirm-dialog",
                        "name": "Confirm Dialog",
                        "href": "/static/dialogs/confirm.js",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = MetaConfig.from_file(metadata_path)

    assert result.plugs == [
        MetaPlug(id="confirm-dialog", name="Confirm Dialog", href="/static/dialogs/confirm.js")
    ]


def test_from_file_rejects_id_name_only_plug(metadata_path):
    metadata_path.write_text(
        yaml.safe_dump(
            {
                "openapi": "/bypass/openapi.json",
                "version": "1.0.0",
                "events": [],
                "plugs": [{"id": "orphan", "name": "Orphan"}],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="must declare a socket, an href, or both"):
        MetaConfig.from_file(metadata_path)


def test_to_file_omits_modal_plug_socket(metadata_path):
    meta_config = MetaConfig(
        openapi="/bypass/openapi.json",
        version="1.0.0",
        events=[],
        plugs=[MetaPlug(id="confirm-dialog", name="Confirm Dialog", href="/static/confirm.js")],
    )

    meta_config.to_file(metadata_path)  # act

    written_payload = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    assert written_payload["plugs"] == [
        {"id": "confirm-dialog", "name": "Confirm Dialog", "href": "/static/confirm.js"}
    ]


def test_to_file_omits_container_plug_href(metadata_path):
    meta_config = MetaConfig(
        openapi="/bypass/openapi.json",
        version="1.0.0",
        events=[],
        plugs=[MetaPlug(id="learn-extensions", name="Learn Extensions", socket="portal")],
    )

    meta_config.to_file(metadata_path)  # act

    written_payload = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    assert written_payload["plugs"] == [
        {"id": "learn-extensions", "name": "Learn Extensions", "socket": "portal"}
    ]
