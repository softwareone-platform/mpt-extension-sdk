import httpx

from mpt_extension_sdk.mpt_http.mpt import _has_more_pages
from mpt_extension_sdk.mpt_http.wrap_http_error import wrap_mpt_http_error


async def _paginated_a(
    mpt_client: httpx.AsyncClient,
    url: str,
    params: dict[str, str | None],
    limit: int = 10,
) -> list[dict]:
    items = []
    page = None
    offset = 0
    while _has_more_pages(page):
        params = {**params, "limit": limit, "offset": offset}
        response = await mpt_client.get(f"{url}", params=params)
        response.raise_for_status()
        page = response.json()
        items.extend(page["data"])
        offset += limit

    return items


@wrap_mpt_http_error
def get_agreements_by_query_a(
    mpt_client: httpx.AsyncClient, query: dict[str, str | None], limit: int = 10
):
    url = "/commerce/agreements"
    return _paginated_a(mpt_client, url, query, limit=limit)


def get_agreements_by_3yc_enroll_status_a(
    mpt_client: httpx.AsyncClient, enroll_statuses: tuple[str], status: str = "Active"
):
    param_condition = (
        f"any(parameters.fulfillment,"
        f"and(eq(externalId,3YCEnrollStatus),in(displayValue,({",".join(enroll_statuses)}))))"
    )
    status_condition = f"eq(status,{status})"

    rql_query = {
        f"and({status_condition},{param_condition})": None,
        "select": "lines,parameters,subscriptions,product,listing",
    }
    return get_agreements_by_query_a(mpt_client, rql_query)
