from mpt_extension_sdk.api import APIContext
from mpt_extension_sdk.observability import trace_span


class SyncAgreements:
    """Mock agreement sync use case."""

    @trace_span("sync_agreements")
    async def execute(self, ctx: APIContext) -> None:
        """Sync agreements."""
        ctx.logger.info("Sync agreements")
        offset = 0
        limit = 5
        while True:
            page = await ctx.mpt_api_service.agreements.get_all(offset=offset, limit=limit)
            for agreement in page.resources:
                ctx.logger.info("Syncing agreement %s", agreement.id)
                self._sync_agreement(agreement.id)
                ctx.logger.info("Agreement %s synced", agreement.id)
            offset += limit
            if offset >= page.total or not page.resources:
                break

    @trace_span(
        "sync_agreement",
        attributes={
            "agreement.id": lambda _, agreement_id: agreement_id,
        },
    )
    def _sync_agreement(self, agreement_id: str) -> None:
        """Sync a single agreement."""
