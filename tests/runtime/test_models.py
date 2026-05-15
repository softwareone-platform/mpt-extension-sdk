from pathlib import Path

import pytest
import yaml

from mpt_extension_sdk.errors.runtime import ConfigError
from mpt_extension_sdk.runtime.models import MetaConfig, MetaPlug


def test_meta_config_from_file_reads_yaml(meta_config, tmp_path):
    metadata_path = tmp_path / "meta.yaml"
    metadata_path.write_text(
        yaml.safe_dump(meta_config.model_dump(exclude_none=True, by_alias=True), sort_keys=False),
        encoding="utf-8",
    )

    result = MetaConfig.from_file(metadata_path)

    assert result == meta_config


def test_from_file_rejects_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="Metadata file was not found"):
        MetaConfig.from_file(tmp_path / "missing.yaml")


def test_from_file_rejects_non_mapping_root(tmp_path):
    metadata_path = tmp_path / "meta.yaml"
    metadata_path.write_text(yaml.safe_dump(["bad-root"]), encoding="utf-8")

    with pytest.raises(ConfigError, match="Metadata root must be a mapping"):
        MetaConfig.from_file(metadata_path)


def test_from_file_rejects_invalid_schema(tmp_path):
    metadata_path = tmp_path / "meta.yaml"
    metadata_path.write_text(
        yaml.safe_dump({"version": "1.0.0", "openapi": "/openapi.json", "events": [{}]}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="Invalid metadata schema"):
        MetaConfig.from_file(metadata_path)


def test_meta_config_to_file_writes_yaml(meta_config, tmp_path):
    metadata_path = tmp_path / "meta.yaml"

    meta_config.to_file(metadata_path)  # act

    assert Path(metadata_path).read_text(encoding="utf-8") == yaml.safe_dump(
        meta_config.model_dump(exclude_none=True, by_alias=True),
        sort_keys=False,
        allow_unicode=False,
    )


def test_meta_config_supports_plugs(tmp_path):
    metadata_path = tmp_path / "meta.yaml"
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
