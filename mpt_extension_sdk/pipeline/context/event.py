from dataclasses import dataclass, field
from typing import Any

from mpt_extension_sdk.context import BaseContext


@dataclass(frozen=True)
class EventMetadata:
    """Immutable event execution metadata."""

    event_id: str
    object_id: str
    object_type: str
    task_id: str

    correlation_id: str | None = None
    installation_id: str | None = None


@dataclass(kw_only=True)
class EventBaseContext(BaseContext):
    """Mutable context passed through pipeline steps."""

    meta: EventMetadata

    state: dict[str, Any] = field(default_factory=dict)
