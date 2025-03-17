from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Literal

from typing_extensions import Doc

from mpt_extension_sdk.constants import EVENT_TYPES

EventType = Annotated[Literal[EVENT_TYPES], Doc("Unique identifier of the event type.")]


@dataclass
class Event:
    id: Annotated[str, Doc("The unique identifier of the event.")]
    type: EventType
    data: Annotated[Mapping | Sequence, Doc("Event data.")]
