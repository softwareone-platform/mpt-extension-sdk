from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from mpt_extension_sdk.errors.runtime import ConfigError
from mpt_extension_sdk.routing.enums import HTTPMethod
from mpt_extension_sdk.routing.models import TaskTimeouts
from mpt_extension_sdk.routing.validators import RouteValidator


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


class MetaSchedule(BaseModel):
    """Metadata model for a registered schedule."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    cron: str = Field(min_length=1)
    path: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("cron")
    @classmethod
    def validate_cron(cls, cron: str) -> str:
        """Validate the five-field cron format accepted by the framework."""
        if len(cron.split()) != 5:
            raise ValueError("Schedule cron must contain five fields")
        return cron


class MetaTaskTimeouts(BaseModel):
    """Task lifetime limits of a deferrable endpoint, in seconds."""

    # Keep the order of fields in the model consistent with the order in the metadata file
    max_task_lifespan: int | None = Field(
        default=None,
        serialization_alias="maxTaskLifespan",
        validation_alias="maxTaskLifespan",
    )
    max_task_processing: int | None = Field(
        default=None,
        serialization_alias="maxTaskProcessing",
        validation_alias="maxTaskProcessing",
    )

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    @model_validator(mode="after")
    def validate_limits(self) -> Self:
        """Reject a timeouts declaration that carries no limit."""
        TaskTimeouts(
            max_task_lifespan=self.max_task_lifespan,
            max_task_processing=self.max_task_processing,
        )
        return self


class MetaDeferrable(BaseModel):
    """Metadata model for an endpoint that accepts deferred calls."""

    # Keep the order of fields in the model consistent with the order in the metadata file
    path: str = Field(min_length=1)
    method: HTTPMethod
    timeouts: MetaTaskTimeouts | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("path")
    @classmethod
    def validate_path(cls, path: str) -> str:
        """Reject a path parameter, which the platform does not resolve for a deferred call."""
        RouteValidator.validate_deferrable_options(path=path, deferrable=True, timeouts=None)
        return path


class MetaConfig(BaseModel):
    """MetaConfig model for loading metadata."""

    # Keep the order of fields in the model consistent with the order in the metadata file
    openapi: str = Field(min_length=1)
    version: str = Field(default="1.0.0", min_length=1)

    events: list[MetaEvent]
    schedules: list[MetaSchedule] | None = None
    plugs: list[MetaPlug] | None = None
    deferrables: list[MetaDeferrable] | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_unique_deferrables(self) -> Self:
        """Reject a method and path pair declared twice in the deferrables block."""
        RouteValidator.validate_deferrable_uniqueness(
            (deferrable.method, deferrable.path) for deferrable in self.deferrables or []
        )
        return self

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
                self.model_dump(exclude_none=True, by_alias=True, mode="json"),
                sort_keys=False,
                allow_unicode=False,
            ),
            encoding="utf-8",
        )
