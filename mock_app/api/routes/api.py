from mock_app.api.schemas import AgreementSchema
from mock_app.sync.agreements import SyncAgreements
from mpt_extension_sdk import APIRouter
from mpt_extension_sdk.api import APIContext, APIResponse, NotFoundError, PaginatedResult

api_router = APIRouter()


@api_router.get("/agreements/{agreement_id}", name="agreement-retrieve")
async def handle_get_agreement(agreement_id: str, ctx: APIContext) -> APIResponse:
    """Return one agreement using the authenticated MPT API service."""
    if agreement_id == "not-found":
        raise NotFoundError(f"Agreement {agreement_id} not found")

    agreement = await ctx.mpt_api_service.agreements.get_by_id(agreement_id)
    return APIResponse.ok(payload=agreement)


@api_router.get("/agreements", name="agreements-list")
async def handle_get_agreements(ctx: APIContext) -> APIResponse:
    """Return paginated mock agreements."""
    agreements = await ctx.mpt_api_service.agreements.get_all(batch_size=3)  # type: ignore[attr-defined]
    result = PaginatedResult.from_pagination(ctx.request.pagination, payload=agreements, total=10)
    return APIResponse.paginated(result)


@api_router.post("/agreements", name="agreements-create", body_validator=AgreementSchema)
async def handle_create_agreement(body: AgreementSchema, ctx: APIContext) -> APIResponse:
    """Create one agreement through the mock service facade."""
    new_agreement = await ctx.mpt_api_service.agreements.create(body)  # type: ignore[attr-defined]
    return APIResponse.created(payload=new_agreement)


@api_router.post("/agreements/sync", name="agreements-sync")
async def handle_sync_agreements(ctx: APIContext) -> APIResponse:
    """Trigger the mock agreement sync flow."""
    await SyncAgreements().execute(ctx)
    return APIResponse.no_content()
