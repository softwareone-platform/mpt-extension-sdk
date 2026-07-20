from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from mpt_extension_sdk.errors.runtime import ConfigError


class MetaEvent(BaseModel):
    """MetaEvent model for loading metadata."""

    # Keep the order of fields in the model consistent with the order in the metadata file
    event: str = Field(min_length=1)
    condition: str | None = Field(default=None, min_length=1)
    path: str = Field(min_length=1)
    task: bool

    model_config = ConfigDict(extra="forbid")


class MetaPlug(BaseModel):
    """MetaPlug model for loading metadata.

    Navigation-container plugs ship no bundle, so `href` always stays unset;
    `description` is optional and may be populated when the container declares one.
    Modal (open-by-id) plugs are never mounted on a socket, so `socket` stays unset
    for them.
    """

    # Keep the order of fields in the model consistent with the order in the metadata file
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str | None = Field(default=None, min_length=1)
    icon: str | None = Field(default=None, min_length=1)
    socket: str | None = Field(default=None, min_length=1)
    condition: str | None = Field(default=None, min_length=1)
    href: str | None = Field(default=None, min_length=1)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_socket_or_href(self) -> Self:
        """Reject plug entries that declare neither a socket nor an href."""
        if self.socket is None and self.href is None:
            raise ValueError("Plug metadata must declare a socket, an href, or both")
        return self


class MetaConfig(BaseModel):
    """MetaConfig model for loading metadata."""

    # Keep the order of fields in the model consistent with the order in the metadata file
    openapi: str = Field(min_length=1)
    version: str = Field(default="1.0.0", min_length=1)

    events: list[MetaEvent]
    plugs: list[MetaPlug] | None = None

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_file(cls, path: Path) -> Self:
        """Load metadata from a YAML file."""
        if not path.exists():
            raise ConfigError(f"Metadata file was not found: {path}")

        with path.open(encoding="utf-8") as metadata_file:
            raw_payload: Any = yaml.safe_load(metadata_file)

        if not isinstance(raw_payload, dict):
            raise ConfigError("Metadata root must be a mapping")
        try:
            return cls.model_validate(raw_payload, by_alias=True)
        except ValidationError as error:
            raise ConfigError(f"Invalid metadata schema: {error}") from error

    def to_file(self, path: Path) -> None:
        """Persist metadata to a YAML file.

        Args:
            path: Destination metadata path.
        """
        path.write_text(
            yaml.safe_dump(
                self.model_dump(exclude_none=True, by_alias=True),
                sort_keys=False,
                allow_unicode=False,
            ),
            encoding="utf-8",
        )
