from mpt_api_client import RQLQuery

from mpt_extension_sdk.models import Product, ProductItem
from mpt_extension_sdk.services.mpt_api_service.base import BaseService

_MAX_PAGE_SIZE = 100


class ProductService(BaseService[Product]):
    """Product service."""


class ProductItemService(BaseService[ProductItem]):
    """Product item service."""

    async def get_product_one_time_items_by_ids(
        self, product_id: str, item_ids: list[str]
    ) -> list[ProductItem]:
        """Fetch one-time items by product and item identifiers."""
        if not item_ids:
            return []
        resources: list[ProductItem] = []
        for start in range(0, len(item_ids), _MAX_PAGE_SIZE):
            chunk_ids = item_ids[start : start + _MAX_PAGE_SIZE]
            chunk_query = (
                RQLQuery(product__id=product_id)
                & RQLQuery().id.in_(chunk_ids)  # type: ignore[arg-type]
                & RQLQuery().n("terms.period").eq("one-time")
            )
            page = await self._paginate(  # noqa: WPS476
                self._client.catalog.items.filter(chunk_query),
                ProductItem,
                limit=len(chunk_ids),
            )
            resources.extend(page.resources)
        return resources
