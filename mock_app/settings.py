from typing import Self, override

from mpt_extension_sdk.settings.extension import BaseExtensionSettings


class ExtensionSettings(BaseExtensionSettings):
    """Extension settings."""

    @override
    @classmethod
    def load(cls) -> Self:
        """Load settings."""
        return cls()
