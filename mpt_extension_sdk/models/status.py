import warnings
from enum import StrEnum
from typing import override


class UnknownStatusWarning(UserWarning):
    """Signals that a platform object reported a status outside its known set."""


class CaseInsensitiveStrEnum(StrEnum):
    """StrEnum that resolves values case-insensitively through the `_missing_` hook."""

    @classmethod
    @override
    def _missing_(cls, status_value: object) -> "CaseInsensitiveStrEnum | None":  # noqa: WPS120 - Python Enum hook.
        if not isinstance(status_value, str):
            return None
        normalized_value = status_value.lower()
        for member in cls:
            if member.value.lower() == normalized_value:
                return member
        return None


def warn_on_unknown_status(
    object_label: str,
    object_id: str,
    status: object,
    known_status_type: type[StrEnum],
    warning_type: type[UnknownStatusWarning],
) -> None:
    """Emit `warning_type` when `status` is not a member of `known_status_type`."""
    if not isinstance(status, known_status_type):
        warnings.warn(
            f"{object_label} {object_id} reported unknown status {status!r}",
            warning_type,
            stacklevel=3,
        )
