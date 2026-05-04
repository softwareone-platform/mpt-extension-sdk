from mock_app.sync.agreements import SyncAdobeAgreements
from mpt_extension_sdk import APIRouter
from mpt_extension_sdk.api import APIContext, APIResponse, PaginatedResult
from mpt_extension_sdk.api.errors import NotFoundError
from mpt_extension_sdk.schemas import BaseSchema

api_router = APIRouter()


@api_router.get("/agreements/{agreement_id}", name="agreement-retrieve")
async def handler_get_agreement(agreement_id: str, ctx: APIContext) -> APIResponse:
    """Return one agreement using the authenticated MPT API service."""
    if agreement_id == "not-found":
        raise NotFoundError(f"Agreement {agreement_id} not found")

    agreement = await ctx.mpt_api_service.agreements.get_by_id(agreement_id)
    return APIResponse.ok(payload=agreement)


@api_router.get("/agreements", name="agreements-list")
async def handler_get_agreements(ctx: APIContext) -> APIResponse:
    """Return one agreement using the authenticated MPT API service."""
    agreements = await ctx.mpt_api_service.agreements.get_all(batch_size=3)  # type: ignore[attr-defined]
    result = PaginatedResult.from_pagination(ctx.request.pagination, payload=agreements, total=10)
    return APIResponse.paginated(result)


@api_router.post("/agreements/sync", name="agreements-sync")
async def handler_sync_agreement(ctx: APIContext) -> APIResponse:
    """Trigger the mock agreement sync flow."""
    await SyncAdobeAgreements().execute(ctx)
    return APIResponse.no_content()


class AgreementSchema(BaseSchema):
    """Schema used by the mock creation agreement endpoint."""

    id: str
    name: str
    client: dict[str, str]
    licensee: dict[str, str]
    parameters: dict[str, str]  # noqa: WPS110
    product: dict[str, str]


@api_router.post("/agreements", name="agreements-create", body_validator=AgreementSchema)
async def handler_create_agreement(body: AgreementSchema, ctx: APIContext) -> APIResponse:
    """Create one agreement through the authenticated service façade."""
    new_agreement = await ctx.mpt_api_service.agreements.create(body)
    return APIResponse.created(payload=new_agreement)
