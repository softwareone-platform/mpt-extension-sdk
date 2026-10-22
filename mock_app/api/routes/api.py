from mock_app.api.schemas import AgreementSchema
from mock_app.sync.agreements import SyncAgreements
from mpt_extension_sdk import APIRouter, TaskTimeouts
from mpt_extension_sdk.api import APIContext, APIResponse, NotFoundError, PaginatedResult

SYNC_MAX_TASK_PROCESSING_SECONDS = 600

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
    pagination = ctx.request.pagination
    page = await ctx.mpt_api_service.agreements.get_all(
        offset=pagination.offset, limit=pagination.limit
    )
    result = PaginatedResult.from_pagination(pagination, payload=page.resources, total=page.total)
    return APIResponse.paginated(result)


@api_router.get("/vendor/agreements", name="vendor-agreements-list")
async def handle_get_vendor_agreements(ctx: APIContext) -> APIResponse:
    """Return paginated agreements read as the vendor account owning the extension."""
    pagination = ctx.request.pagination
    page = await ctx.vendor_mpt_api_service.agreements.get_all(
        offset=pagination.offset, limit=pagination.limit
    )
    result = PaginatedResult.from_pagination(pagination, payload=page.resources, total=page.total)
    return APIResponse.paginated(result)


@api_router.post("/agreements", name="agreements-create", body_validator=AgreementSchema)
async def handle_create_agreement(body: AgreementSchema, ctx: APIContext) -> APIResponse:
    """Create one agreement through the mock service facade."""
    new_agreement = await ctx.mpt_api_service.agreements.create(body)  # type: ignore[attr-defined]
    return APIResponse.created(payload=new_agreement)


@api_router.post(
    "/agreements/sync",
    name="agreements-sync",
    deferrable=True,
    timeouts=TaskTimeouts(max_task_processing=SYNC_MAX_TASK_PROCESSING_SECONDS),
)
async def handle_sync_agreements(ctx: APIContext) -> APIResponse | None:
    """Run the mock agreement sync flow, directly or as a deferred platform task.

    A direct call waits for the sync and answers 204. A deferred delivery
    (`MPT-Task-Id` header) runs it in the background, reports to the task, and
    returns nothing, so the task status is the whole outcome.
    """
    if ctx.task is None:
        await SyncAgreements().execute(ctx)
        return APIResponse.no_content()

    await ctx.task.log("Starting agreements sync")
    await SyncAgreements().execute(ctx)
    await ctx.task.log("Agreements sync finished")
    return None
