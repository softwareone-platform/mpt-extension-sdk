import datetime as dt

from mpt_extension_sdk.models.base import BaseModel


class User(BaseModel):
    """User model."""

    id: str
    name: str
    revision: int


class AuditData(BaseModel):
    """Audit data model."""

    at: str

    by: User | None = None

    @property
    def timestamp(self) -> dt.datetime | None:
        """The audit time as an aware datetime, tolerating malformed values."""
        try:
            parsed = dt.datetime.fromisoformat(self.at)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=dt.UTC)
        return parsed


class Audit(BaseModel):
    """Audit model."""

    created: AuditData | None = None
    updated: AuditData | None = None
    started: AuditData | None = None
