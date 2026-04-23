from dataclasses import dataclass
from typing import Any, Self, override

from mpt_extension_sdk.settings.extension import BaseExtensionSettings


@dataclass(frozen=True)
class ExtensionSettings(BaseExtensionSettings):
    """Extension settings."""

    product_ids: tuple[str, ...]

    @override
    @property
    def required_env_vars(self) -> list[tuple[Any, ...]]:
        return [
            (self.product_ids, "Product ids is required (MPT_PRODUCTS_IDS)"),
        ]

    @override
    @classmethod
    def load(cls) -> Self:
        return cls(product_ids=tuple(cls.list_env("MPT_PRODUCTS_IDS")))
