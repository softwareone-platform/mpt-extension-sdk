import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from mpt_extension_sdk.routing.enums import RouteType
from mpt_extension_sdk.routing.models import WebhookRouteDefinition
from mpt_extension_sdk.routing.routers.base import BaseExtensionRouter
from mpt_extension_sdk.routing.types import WebhookRouteCallback
from mpt_extension_sdk.webhooks.enums import WebhookType

logger = logging.getLogger(__name__)

type Criteria = Mapping[str, str]
type WebhookCriteria = Criteria | Sequence[Criteria]


@dataclass
class WebhookRouter(BaseExtensionRouter):
    """Router object for platform webhook handlers."""

    def webhook(
        self,
        path: str,
        *,
        type: WebhookType | str,  # ruff:ignore[builtin-argument-shadowing] - metadata contract uses "type"
        description: str,
        criteria: WebhookCriteria,
    ) -> Callable[[WebhookRouteCallback], WebhookRouteCallback]:
        """Register a webhook handler.

        The route name is the handler function name, so it is not part of the
        decorator arguments. `criteria` takes one mapping, or a list of mappings
        to request one platform webhook per mapping on the same route, for
        example one per product.
        """
        webhook_type = self._resolve_type(type)
        if not description.strip():
            raise ValueError("Webhook description cannot be empty")
        criteria_sets = self._validate_criteria_sets(criteria)
        normalized_path = self._join_paths(self.prefix, path)

        def decorator(route_handler: WebhookRouteCallback) -> WebhookRouteCallback:
            self._register_base_route(
                WebhookRouteDefinition(
                    name=route_handler.__name__,
                    path=normalized_path,
                    route_type=RouteType.WEBHOOK,
                    callback=route_handler,
                    criteria_sets=criteria_sets,
                    description=description.strip(),
                    webhook_type=webhook_type,
                )
            )
            return route_handler

        return decorator

    def _criteria_key(self, criteria: Criteria) -> frozenset[tuple[str, str]]:
        return frozenset(criteria.items())

    def _is_filled(self, text: object) -> bool:
        return isinstance(text, str) and bool(text.strip())

    def _resolve_type(self, webhook_type: WebhookType | str) -> WebhookType | str:
        if not webhook_type.strip():
            raise ValueError("Webhook type cannot be empty")
        resolved_type = WebhookType.resolve(webhook_type)
        if not isinstance(resolved_type, WebhookType):
            logger.warning("Webhook type '%s' is not known by the SDK", resolved_type)
        return resolved_type

    def _validate_criteria(self, criteria: Criteria) -> Criteria:
        if not criteria:
            raise ValueError("Webhook criteria cannot be empty")
        if not all(self._is_filled(criteria_key) for criteria_key in criteria):
            raise ValueError("Webhook criteria keys must be non-empty strings")
        for criteria_key, criteria_value in criteria.items():
            if not self._is_filled(criteria_value):
                raise ValueError(
                    f"Webhook criteria value for '{criteria_key}' must be a non-empty string"
                )
        return MappingProxyType(dict(criteria))

    def _validate_criteria_sets(self, criteria: WebhookCriteria) -> tuple[Criteria, ...]:
        criteria_list = [criteria] if isinstance(criteria, Mapping) else list(criteria)
        if not criteria_list:
            raise ValueError("Webhook criteria cannot be empty")
        criteria_sets = tuple(map(self._validate_criteria, criteria_list))
        if len(set(map(self._criteria_key, criteria_sets))) != len(criteria_sets):
            raise ValueError("Webhook criteria cannot be repeated")
        return criteria_sets
