import logging
from dataclasses import dataclass
from typing import Any

from mpt_extension_sdk.runtime.bootstrap.client import register_extension_instance
from mpt_extension_sdk.runtime.bootstrap.identity import load_identity, save_identity
from mpt_extension_sdk.settings.runtime import RuntimeSettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegistrationResult:
    """Registration result payload."""

    instance: dict[str, Any]


def register_instance(settings: RuntimeSettings) -> RegistrationResult:
    """Register an extension instance and persist identity if provided."""
    payload: dict[str, Any] = {
        "externalId": settings.external_id,
        "version": settings.meta_config.version,
        "meta": settings.meta_config.model_dump(by_alias=True),
    }
    logger.info(
        "Registering extension instance extension_id=%s external_id=%s \n events: %s",
        settings.extension_id,
        settings.external_id,
        payload["meta"].get("events", []),
    )

    existing_identity = load_identity(settings.identity_file_path)
    mrok_identity = existing_identity.get("mrok", {})
    if not isinstance(mrok_identity, dict):
        mrok_identity = {}
    if (
        not existing_identity
        or str(mrok_identity.get("extension", "")).lower() != settings.extension_id.lower()
    ):
        payload["channel"] = {}

    instance_payload = register_extension_instance(
        settings.base_url, settings.extension_id, settings.ext_api_key, payload
    )
    identity = instance_payload.get("channel", {}).get("identity")
    if isinstance(identity, dict) and identity:
        save_identity(settings.identity_file_path, identity)

    logger.info("Extension registration completed extension_id=%s", settings.extension_id)
    return RegistrationResult(instance=instance_payload)
