import logging
from collections.abc import Iterable
from functools import cache
from itertools import batched

from django.conf import settings

from mpt_extension_sdk.mpt_http.base import MPTClient
from mpt_extension_sdk.mpt_http.wrap_http_error import wrap_mpt_http_error

logger = logging.getLogger(__name__)


def _has_more_pages(page):
    if not page:
        return True
    pagination = page["$meta"]["pagination"]
    return pagination["total"] > pagination["limit"] + pagination["offset"]


def _paginated(mpt_client, url, limit=10):
    items = []
    page = None
    offset = 0
    while _has_more_pages(page):
        response = mpt_client.get(f"{url}&limit={limit}&offset={offset}")
        response.raise_for_status()
        page = response.json()
        items.extend(page["data"])
        offset += limit

    return items


@wrap_mpt_http_error
def get_agreement(mpt_client, agreement_id):
    response = mpt_client.get(
        f"/commerce/agreements/{agreement_id}?select=seller,buyer,listing,product,subscriptions"
    )
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def get_licensee(mpt_client, licensee_id):
    response = mpt_client.get(f"/accounts/licensees/{licensee_id}")
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def update_order(mpt_client, order_id, **kwargs):
    response = mpt_client.put(
        f"/commerce/orders/{order_id}",
        json=kwargs,
    )
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def query_order(mpt_client, order_id, **kwargs):
    response = mpt_client.post(
        f"/commerce/orders/{order_id}/query",
        json=kwargs,
    )
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def fail_order(mpt_client, order_id, status_notes, **kwargs):
    response = mpt_client.post(
        f"/commerce/orders/{order_id}/fail",
        json={
            "statusNotes": status_notes,
            **kwargs,
        },
    )
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def complete_order(mpt_client, order_id, template, **kwargs):
    response = mpt_client.post(
        f"/commerce/orders/{order_id}/complete",
        json={"template": template, **kwargs},
    )
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def set_processing_template(mpt_client, order_id, template):
    response = mpt_client.put(
        f"/commerce/orders/{order_id}",
        json={"template": template},
    )
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def create_asset(mpt_client, order_id, asset):
    """Create a new asset for an order."""
    response = mpt_client.post(f"/commerce/orders/{order_id}/assets", json=asset)
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def update_asset(mpt_client, order_id, asset_id, **kwargs):
    """Update an order asset."""
    response = mpt_client.put(f"/commerce/orders/{order_id}/assets/{asset_id}", json=kwargs)
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def create_subscription(mpt_client, order_id, subscription):
    response = mpt_client.post(
        f"/commerce/orders/{order_id}/subscriptions",
        json=subscription,
    )
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def update_subscription(mpt_client, order_id, subscription_id, **kwargs):
    response = mpt_client.put(
        f"/commerce/orders/{order_id}/subscriptions/{subscription_id}",
        json=kwargs,
    )
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def get_order_subscription_by_external_id(mpt_client, order_id, subscription_external_id):
    """Retrieve an order subscription by its external ID."""
    response = mpt_client.get(
        f"/commerce/orders/{order_id}/subscriptions?eq(externalIds.vendor,{subscription_external_id})&limit=1",
    )
    response.raise_for_status()
    subscriptions = response.json()
    if subscriptions["$meta"]["pagination"]["total"] == 1:
        return subscriptions["data"][0]


@wrap_mpt_http_error
def get_product_items_by_skus(mpt_client, product_id, skus):
    """Retrieve product items by their SKUs."""
    skus_str = ",".join(skus)
    rql_query = f"and(eq(product.id,{product_id}),in(externalIds.vendor,({skus_str})))"
    url = f"/catalog/items?{rql_query}"
    return _paginated(mpt_client, url)


@cache
@wrap_mpt_http_error
def get_webhook(mpt_client, webhook_id):
    response = mpt_client.get(f"/notifications/webhooks/{webhook_id}?select=criteria")
    response.raise_for_status()

    return response.json()


@wrap_mpt_http_error
def get_product_template_or_default(mpt_client, product_id, status, name=None):
    name_or_default_filter = "eq(default,true)"
    if name:
        name_or_default_filter = f"or({name_or_default_filter},eq(name,{name}))"
    rql_filter = f"and(eq(type,Order{status}),{name_or_default_filter})"
    url = f"/catalog/products/{product_id}/templates?{rql_filter}&order=default&limit=1"
    response = mpt_client.get(url)
    response.raise_for_status()
    templates = response.json()
    return templates["data"][0]


def get_template_by_name(mpt_client, product_id, template_name):
    url = f"/catalog/products/{product_id}/templates?eq(name,{template_name})"
    response = mpt_client.get(url)
    response.raise_for_status()
    templates = response.json()
    return templates["data"][0]


@wrap_mpt_http_error
def update_agreement(mpt_client, agreement_id, **kwargs):
    response = mpt_client.put(
        f"/commerce/agreements/{agreement_id}",
        json=kwargs,
    )
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def get_agreements_by_query(mpt_client, query):
    url = f"/commerce/agreements?{query}"
    return _paginated(mpt_client, url)


@wrap_mpt_http_error
def update_agreement_subscription(mpt_client, subscription_id, **kwargs):
    response = mpt_client.put(
        f"/commerce/subscriptions/{subscription_id}",
        json=kwargs,
    )
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def get_agreement_subscription(mpt_client, subscription_id):
    response = mpt_client.get(
        f"/commerce/subscriptions/{subscription_id}",
    )
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def get_rendered_template(mpt_client, order_id):
    response = mpt_client.get(
        f"/commerce/orders/{order_id}/template",
    )
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def get_product_onetime_items_by_ids(mpt_client, product_id, item_ids):
    product_cond = f"eq(product.id,{product_id})"
    items_cond = f"in(id,({','.join(item_ids)}))"
    rql_query = f"and({product_cond},{items_cond},eq(terms.period,one-time))"
    url = f"/catalog/items?{rql_query}"

    return _paginated(mpt_client, url)


@wrap_mpt_http_error
def get_product_items_by_period(
    mpt_client,
    product_id: str,
    period: str,
    vendor_external_ids: Iterable[str] | None = None,
):
    """
    Fetches product items based on a specified period and filters.

    Args:
        mpt_client: Client in tance to interact with the required API.
        product_id (str): The unique identifier of the product to fetch items for.
        period (str): The period for which to fetch the product items.
        vendor_external_ids (Iterable[str] | None):
            Optional. A list of vendor external IDs to filter out the product items by. Defaults
            to None.

    Returns:
        list:
            A paginated list of product items matching the specified criteria.

    """
    product_cond = f"eq(product.id,{product_id})"
    vendors_cond = ""
    if vendor_external_ids:
        vendor_ids = ",".join(vendor_external_ids)
        vendors_cond = f",in(externalIds.vendor,({vendor_ids})))"
    rql_query = f"and({product_cond},eq(terms.period,{period}){vendors_cond})"
    url = f"/catalog/items?{rql_query}"

    return _paginated(mpt_client, url)


def get_agreements_by_ids(mpt_client, ids):
    rql_query = (
        f"and(in(id,({','.join(ids)})),eq(status,Active))"
        "&select=lines,parameters,subscriptions,product,listing"
    )
    return get_agreements_by_query(mpt_client, rql_query)


def get_all_agreements(
    mpt_client,
):
    product_condition = f"in(product.id,({','.join(settings.MPT_PRODUCTS_IDS)}))"

    return get_agreements_by_query(
        mpt_client,
        f"and(eq(status,Active),{product_condition})&select=lines,parameters,subscriptions,product,listing",
    )


@wrap_mpt_http_error
def get_authorizations_by_currency_and_seller_id(mpt_client, product_id, currency, owner_id):
    """Retrieve authorizations by product ID, currency, and owner ID."""
    authorization_filter = (
        f"eq(product.id,{product_id})&eq(currency,{currency})&eq(owner.id,{owner_id})"
    )
    response = mpt_client.get(f"/catalog/authorizations?{authorization_filter}")
    response.raise_for_status()
    return response.json()["data"]


@wrap_mpt_http_error
def get_gc_price_list_by_currency(mpt_client, product_id, currency):
    response = mpt_client.get(
        f"/catalog/price-lists?eq(product.id,{product_id})&eq(currency,{currency})"
    )
    response.raise_for_status()
    return response.json()["data"]


@wrap_mpt_http_error
def get_listings_by_price_list_and_seller_and_authorization(
    mpt_client, product_id, price_list_id, seller_id, authorization_id
):
    response = mpt_client.get(
        f"/catalog/listings?eq(product.id,{product_id})&eq(priceList.id,{price_list_id})"
        f"&eq(seller.id,{seller_id})"
        f"&eq(authorization.id,{authorization_id})"
    )
    response.raise_for_status()
    return response.json()["data"]


@wrap_mpt_http_error
def create_listing(mpt_client, listing):
    response = mpt_client.post(
        "/catalog/listings",
        json=listing,
    )
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def create_agreement(mpt_client, agreement):
    response = mpt_client.post(
        "/commerce/agreements",
        json=agreement,
    )
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def create_agreement_subscription(mpt_client, subscription):
    response = mpt_client.post(
        "/commerce/subscriptions",
        json=subscription,
    )
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def get_listing_by_id(mpt_client, listing_id):
    response = mpt_client.get(f"/catalog/listings/{listing_id}")
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def get_agreement_subscription_by_external_id(mpt_client, agreement_id, subscription_external_id):
    """Retrieve an agreement subscription by external ID."""
    response = mpt_client.get(
        f"/commerce/subscriptions?eq(externalIds.vendor,{subscription_external_id})"
        f"&eq(agreement.id,{agreement_id})"
        f"&in(status,(Active,Updating))"
        f"&select=agreement.id&limit=1"
    )

    response.raise_for_status()
    subscriptions = response.json()
    return subscriptions["data"][0] if subscriptions["data"] else None


@wrap_mpt_http_error
def get_agreements_by_external_id_values(mpt_client, external_id, display_values):
    display_values_list = ",".join(display_values)
    rql_query = (
        f"any(parameters.fulfillment,and("
        f"eq(externalId,{external_id}),"
        f"in(displayValue,({display_values_list}))))"
        f"&select=lines,parameters,subscriptions,product,listing"
    )

    url = f"/commerce/agreements?{rql_query}"

    return _paginated(mpt_client, url)


@wrap_mpt_http_error
def get_agreements_by_customer_deployments(mpt_client, deployment_id_parameter, deployment_ids):
    """Retrieve agreements by customer deployments."""
    deployments_list = ",".join(deployment_ids)
    rql_query = (
        f"any(parameters.fulfillment,and("
        f"eq(externalId,{deployment_id_parameter}),"
        f"in(displayValue,({deployments_list}))))"
        f"&select=lines,parameters,subscriptions,subscriptions.parameters,product,listing"
    )

    url = f"/commerce/agreements?{rql_query}"

    return _paginated(mpt_client, url)


@wrap_mpt_http_error
def get_buyer(mpt_client, buyer_id):
    response = mpt_client.get(f"/accounts/buyers/{buyer_id}")
    response.raise_for_status()
    return response.json()


@wrap_mpt_http_error
def notify(
    mpt_client: MPTClient,
    category_id: str,
    account_id: str,
    buyer_id: str,
    subject: str,
    message_body: str,
    limit: int = 1000,
) -> None:
    """
    Sends notifications to multiple recipients in batches for a specific buyer and
    category through the MPTClient service. The function retrieves recipients,
    groups them into manageable batches, and sends notifications using the provided
    message details.
    """
    recipients = _paginated(
        mpt_client,
        url=(
            f"notifications/accounts/{account_id}/categories/{category_id}/contacts?"
            f"select=id,-email,-name,-status,-user&"
            f"filter(group.buyers.id,{buyer_id})"
        ),
        limit=limit,
    )

    for contacts in batched(recipients, limit):
        response = mpt_client.post(
            "notifications/batches",
            json={
                "category": {"id": category_id},
                "subject": subject,
                "body": message_body,
                "contacts": contacts,
                "buyer": {"id": buyer_id},
            },
        )
        response.raise_for_status()


@wrap_mpt_http_error
def terminate_subscription(mpt_client: MPTClient, subscription_id: str, reason: str) -> dict:
    """
    Terminates a subscription by calling the MPT API.

    Raises:
        HTTPError: If the HTTP request fails, an HTTPError is raised with
            information about the issue.
    """
    response = mpt_client.post(
        f"/commerce/subscriptions/{subscription_id}/terminate",
        json={"description": reason},
    )
    response.raise_for_status()

    return response.json()
