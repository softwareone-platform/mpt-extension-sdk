from mpt_extension_sdk.api import APIContext
from mpt_extension_sdk.observability import trace_span


class SyncAdobeAgreements:
    """Mock agreement sync use case."""

    @trace_span("adobe.sync_agreements")
    async def execute(self, ctx: APIContext) -> None:
        """Sync Adobe agreements."""
        ctx.logger.info("Sync Adobe agreements")
        agreements = await ctx.mpt_api_service.agreements.get_all(batch_size=5)  # type: ignore[attr-defined]
        for agreement in agreements:
            ctx.logger.info("Syncing agreement %s", agreement.id)
            self._sync_agreement(agreement.id)
            ctx.logger.info("Agreement %s synced", agreement.id)

    @trace_span(
        "adobe.sync_agreement",
        attributes={
            "agreement.id": lambda _, agreement_id: agreement_id,
        },
    )
    def _sync_agreement(self, agreement_id: str) -> None:
        """Sync a single agreement."""
