from dataclasses import dataclass
from enum import StrEnum


class AccountType(StrEnum):
    """Supported authenticated account types."""

    CLIENT = "Client"
    OPERATIONS = "Operations"
    VENDOR = "Vendor"


@dataclass(frozen=True)
class Account:
    """Account identity derived from trusted request claims."""

    id: str
    type: AccountType

    def is_client(self) -> bool:
        """Return whether the current account is a client account."""
        return self.type is AccountType.CLIENT

    def is_operations(self) -> bool:
        """Return whether the current account is an operations account."""
        return self.type is AccountType.OPERATIONS

    def is_vendor(self) -> bool:
        """Return whether the current account is a vendor account."""
        return self.type is AccountType.VENDOR


@dataclass(frozen=True)
class AuthContext:
    """Authenticated request context extracted from the caller JWT."""

    token: str
    account: Account
    permissions: dict[str, list[str]]
    extension_id: str
