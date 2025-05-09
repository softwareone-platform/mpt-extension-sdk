import json
from datetime import UTC, datetime
from importlib.metadata import EntryPoint, EntryPoints

import pytest
import responses
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from django.conf import settings
from rich.highlighter import ReprHighlighter as _ReprHighlighter

from mpt_extension_sdk.constants import (
    DEFAULT_APP_CONFIG_GROUP,
    DEFAULT_APP_CONFIG_NAME,
    DJANGO_SETTINGS_MODULE,
)
from mpt_extension_sdk.core.events.dataclasses import Event


@pytest.fixture()
def mock_valid_env_values(
    mock_env_webhook_secret,
    mock_env_airtable_base,
    mock_env_airtable_pricing_base,
    mock_env_product_segment,
    mock_email_notification_sender,
):
    return {
        "EXT_WEBHOOKS_SECRETS": mock_env_webhook_secret,
        "EXT_AIRTABLE_BASES": mock_env_airtable_base,
        "EXT_AIRTABLE_PRICING_BASES": mock_env_airtable_pricing_base,
        "EXT_PRODUCT_SEGMENT": mock_env_product_segment,
        "EXT_EMAIL_NOTIFICATION_SENDER": mock_email_notification_sender,
    }


@pytest.fixture()
def mock_env_webhook_secret():
    return '{ "webhook_secret": "WEBHOOK_SECRET" }'


@pytest.fixture()
def mock_env_airtable_base():
    return '{ "airtable_base": "AIRTABLE_BASE" }'


@pytest.fixture()
def mock_env_airtable_pricing_base():
    return '{ "airtable_pricing_base": "AIRTABLE_PRICING_BASE" }'


@pytest.fixture()
def mock_env_product_segment():
    return '{ "product_segment": "PRODUCT_SEGMENT" }'


@pytest.fixture()
def mock_email_notification_sender():
    return "email_sender"


@pytest.fixture()
def mock_invalid_env_values(
    mock_env_webhook_secret,
    mock_env_airtable_base,
    mock_env_airtable_pricing_base,
    mock_env_invalid_product_segment,
    mock_email_notification_sender,
):
    return {
        "EXT_WEBHOOKS_SECRETS": mock_env_webhook_secret,
        "EXT_AIRTABLE_BASES": mock_env_airtable_base,
        "EXT_AIRTABLE_PRICING_BASES": mock_env_airtable_pricing_base,
        "EXT_PRODUCT_SEGMENT": mock_env_invalid_product_segment,
        "EXT_EMAIL_NOTIFICATION_SENDER": mock_email_notification_sender,
    }


@pytest.fixture()
def mock_gunicorn_logging_config():
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{asctime} {name} {levelname} (pid: {process}) {message}",
                "style": "{",
            },
            "rich": {
                "format": "%(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
            "rich": {
                "class": "rich.logging.RichHandler",
                "formatter": "rich",
                "log_time_format": lambda x: x.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "rich_tracebacks": True,
            },
        },
        "root": {
            "handlers": ["rich"],
            "level": "INFO",
        },
        "loggers": {
            "gunicorn.access": {
                "handlers": ["rich"],
                "level": "INFO",
                "propagate": False,
            },
            "gunicorn.error": {
                "handlers": ["rich"],
                "level": "INFO",
                "propagate": False,
            },
            "swo.mpt": {},
        },
    }


@pytest.fixture()
def runtime_master_options_factory(
    component="all",
):
    def _runtime_master_options(
        component=component,
    ):
        return {
            "color": True,
            "debug": False,
            "reload": True,
            "component": component,
        }

    return _runtime_master_options


@pytest.fixture()
def mock_highlights(mock_logging_all_prefixes):
    return _ReprHighlighter.highlights + [
        rf"(?P<mpt_id>(?:{'|'.join(mock_logging_all_prefixes)})(?:-\d{{4}})*)"
    ]


@pytest.fixture()
def mock_logging_account_prefixes():
    return ("ACC", "BUY", "LCE", "MOD", "SEL", "USR", "AUSR", "UGR")


@pytest.fixture()
def mock_logging_catalog_prefixes():
    return (
        "PRD",
        "ITM",
        "IGR",
        "PGR",
        "MED",
        "DOC",
        "TCS",
        "TPL",
        "WHO",
        "PRC",
        "LST",
        "AUT",
        "UNT",
    )


@pytest.fixture()
def mock_logging_commerce_prefixes():
    return ("AGR", "ORD", "SUB", "REQ")


@pytest.fixture()
def mock_logging_aux_prefixes():
    return ("FIL", "MSG")


@pytest.fixture()
def mock_logging_all_prefixes(
    mock_logging_account_prefixes,
    mock_logging_catalog_prefixes,
    mock_logging_commerce_prefixes,
    mock_logging_aux_prefixes,
):
    return (
        *mock_logging_account_prefixes,
        *mock_logging_catalog_prefixes,
        *mock_logging_commerce_prefixes,
        *mock_logging_aux_prefixes,
    )


@pytest.fixture()
def mock_env_invalid_product_segment():
    return '{ "field_1": , , "field2": "very bad json"}'


@pytest.fixture()
def mock_ext_expected_environment_values(
    mock_env_webhook_secret,
    mock_env_airtable_base,
    mock_env_airtable_pricing_base,
    mock_env_product_segment,
    mock_email_notification_sender,
):
    return {
        "WEBHOOKS_SECRETS": json.loads(mock_env_webhook_secret),
        "AIRTABLE_BASES": json.loads(mock_env_airtable_base),
        "AIRTABLE_PRICING_BASES": json.loads(mock_env_airtable_pricing_base),
        "PRODUCT_SEGMENT": json.loads(mock_env_product_segment),
        "EMAIL_NOTIFICATION_SENDER": mock_email_notification_sender,
    }


@pytest.fixture()
def mock_worker_initialize(mocker):
    return mocker.patch("mpt_extension_sdk.runtime.workers.initialize")


@pytest.fixture()
def mock_worker_call_command(mocker):
    return mocker.patch("mpt_extension_sdk.runtime.workers.call_command")


@pytest.fixture()
def mock_worker_get_entry_points(
    mocker,
    mock_entry_points,
):
    return mocker.patch(
        "mpt_extension_sdk.runtime.utils.entry_points",
        return_value=mock_entry_points,
    )


@pytest.fixture()
def mock_worker_select_entry_point(
    mocker,
    mock_select_entry_point,
):
    return mocker.patch(
        "importlib.metadata.EntryPoints.select",
        return_value=mock_select_entry_point,
    )


@pytest.fixture()
def mock_select_entry_point():
    return EntryPoint(
        name="ep-test-1",
        value="ep-test-1-value",
        group="ep-test-1-group",
    )


@pytest.fixture()
def mock_entry_points():
    return EntryPoints(
        EntryPoint(
            name="ep-test-1",
            value="ep-test-1-value",
            group="ep-test-1-group",
        ),
        EntryPoint(
            name="ep-test-2",
            value="ep-test-2-value",
            group="ep-test-2-group",
        ),
    )


@pytest.fixture()
def mock_app_config():
    return list(
        {
            "__name__": "config_name",
            "__label__": "config_label",
        },
    )


@pytest.fixture()
def mock_json_ext_variables():
    return {
        "EXT_WEBHOOKS_SECRETS",
        "EXT_AIRTABLE_BASES",
        "EXT_AIRTABLE_PRICING_BASES",
        "EXT_PRODUCT_SEGMENT",
    }


@pytest.fixture()
def requests_mocker():
    """
    Allow mocking of http calls made with requests.
    """
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture()
def mpt_client(settings):
    """
    Create an instance of the MPT client used by the extension.
    """
    settings.MPT_API_BASE_URL = "https://localhost"
    from mpt_extension_sdk.core.utils import setup_client

    return setup_client()


@pytest.fixture()
def mpt_operations_client(settings):
    """
    Create an instance of the MPT client used by the extension.
    """
    settings.MPT_API_BASE_URL = "https://localhost"
    from mpt_extension_sdk.core.utils import setup_operations_client

    return setup_operations_client()


@pytest.fixture()
def mpt_error_factory():
    """
    Generate an error message returned by the Marketplace platform.
    """

    def _mpt_error(
        status,
        title,
        detail,
        trace_id="00-27cdbfa231ecb356ab32c11b22fd5f3c-721db10d009dfa2a-00",
        errors=None,
    ):
        error = {
            "status": status,
            "title": title,
            "detail": detail,
            "traceId": trace_id,
        }
        if errors:
            error["errors"] = errors

        return error

    return _mpt_error


@pytest.fixture()
def mock_generic_response_error():
    """
    Generate an HTTP error response.
    """
    return {
        "status_code": 400,
        "content": "bad request",
    }


@pytest.fixture()
def mock_http_response_error():
    """
    Generate an HTTP error response.
    """
    return HttpResponseError(
        message="Request failed",
        request=None,
        response=None,
    )


@pytest.fixture()
def mock_resource_not_found_error():
    """
    Generate a resource not found error.
    """
    return ResourceNotFoundError(
        message="Resource not found",
        request=None,
        response=None,
    )


@pytest.fixture()
def buyer():
    return {
        "id": "BUY-3731-7971",
        "href": "/accounts/buyers/BUY-3731-7971",
        "name": "A buyer",
        "icon": "/static/BUY-3731-7971/icon.png",
        "address": {
            "country": "US",
            "state": "CA",
            "city": "San Jose",
            "addressLine1": "3601 Lyon St",
            "addressLine2": "",
            "postCode": "94123",
        },
        "contact": {
            "firstName": "Cic",
            "lastName": "Faraone",
            "email": "francesco.faraone@softwareone.com",
            "phone": {
                "prefix": "+1",
                "number": "4082954078",
            },
        },
    }


@pytest.fixture()
def licensee(buyer):
    return {
        "id": "LCE-1111-2222-3333",
        "name": "FF Buyer good enough",
        "useBuyerAddress": True,
        "address": buyer["address"],
        "contact": buyer["contact"],
        "buyer": buyer,
        "account": {
            "id": "ACC-1234-1234",
            "name": "Client Account",
        },
    }


@pytest.fixture()
def listing(buyer):
    return {
        "id": "LST-9401-9279",
        "href": "/listing/LST-9401-9279",
        "priceList": {
            "id": "PRC-9457-4272-3691",
            "href": "/v1/price-lists/PRC-9457-4272-3691",
            "currency": "USD",
        },
        "product": {
            "id": "PRD-1234-1234",
            "name": "Adobe for Commercial",
        },
        "vendor": {
            "id": "ACC-1234-vendor-id",
            "name": "Adobe",
        },
    }


@pytest.fixture()
def agreement(buyer, licensee, listing):
    return {
        "id": "AGR-2119-4550-8674-5962",
        "href": "/commerce/agreements/AGR-2119-4550-8674-5962",
        "icon": None,
        "name": "Product Name 1",
        "audit": {
            "created": {
                "at": "2023-12-14T18:02:16.9359",
                "by": {"id": "USR-0000-0001"},
            },
            "updated": None,
        },
        "subscriptions": [
            {
                "id": "SUB-1000-2000-3000",
                "status": "Active",
                "lines": [
                    {
                        "id": "ALI-0010",
                        "item": {
                            "id": "ITM-1234-1234-1234-0010",
                            "name": "Item 0010",
                            "externalIds": {
                                "vendor": "external-id1",
                            },
                        },
                        "quantity": 10,
                    }
                ],
            },
            {
                "id": "SUB-1234-5678",
                "status": "Terminated",
                "lines": [
                    {
                        "id": "ALI-0011",
                        "item": {
                            "id": "ITM-1234-1234-1234-0011",
                            "name": "Item 0011",
                            "externalIds": {
                                "vendor": "external-id2",
                            },
                        },
                        "quantity": 4,
                    }
                ],
            },
        ],
        "listing": listing,
        "licensee": licensee,
        "buyer": buyer,
        "seller": {
            "id": "SEL-9121-8944",
            "href": "/accounts/sellers/SEL-9121-8944",
            "name": "Software LN",
            "icon": "/static/SEL-9121-8944/icon.png",
            "address": {
                "country": "US",
            },
        },
        "product": {
            "id": "PRD-1111-1111",
        },
        "externalId": "external_id",
        "displayValue": "Product Name 1",
    }


@pytest.fixture()
def order_parameters_factory():
    def _order_parameters(
        company_name="FF Buyer good enough",
        address=None,
        contact=None,
    ):
        if address is None:
            address = {
                "country": "US",
                "state": "CA",
                "city": "San Jose",
                "addressLine1": "3601 Lyon St",
                "addressLine2": "",
                "postCode": "94123",
            }
        if contact is None:
            contact = {
                "firstName": "Cic",
                "lastName": "Faraone",
                "email": "francesco.faraone@softwareone.com",
                "phone": {
                    "prefix": "+1",
                    "number": "4082954078",
                },
            }
        return [
            {
                "id": "PAR-0000-0001",
                "name": "Company Name",
                "externalId": "ext-company-name",
                "type": "SingleLineText",
                "value": company_name,
                "constraints": {
                    "hidden": False,
                    "required": True,
                },
            },
            {
                "id": "PAR-0000-0002",
                "name": "Address",
                "externalId": "ext-address",
                "type": "Address",
                "value": address,
                "constraints": {
                    "hidden": False,
                    "required": True,
                },
            },
            {
                "id": "PAR-0000-0003",
                "name": "Contact",
                "externalId": "ext-contact",
                "type": "Contact",
                "value": contact,
                "constraints": {
                    "hidden": False,
                    "required": True,
                },
            },
        ]

    return _order_parameters


@pytest.fixture()
def fulfillment_parameters_factory():
    def _fulfillment_parameters(
        customer_id="",
    ):
        return [
            {
                "id": "PAR-1234-5678",
                "name": "Customer Id",
                "externalId": "ext-customer-id",
                "type": "SingleLineText",
                "value": customer_id,
            },
        ]

    return _fulfillment_parameters


@pytest.fixture()
def lines_factory(agreement):
    agreement_id = agreement["id"].split("-", 1)[1]

    def _items(
        line_id=1,
        item_id=1,
        name="Awesome product",
        old_quantity=0,
        quantity=170,
        external_vendor_id="65304578CA",
        unit_purchase_price=1234.55,
    ):
        line = {
            "item": {
                "id": f"ITM-1234-1234-1234-{item_id:04d}",
                "name": name,
                "externalIds": {
                    "vendor": external_vendor_id,
                },
            },
            "oldQuantity": old_quantity,
            "quantity": quantity,
            "price": {
                "unitPP": unit_purchase_price,
            },
        }
        if line_id:
            line["id"] = f"ALI-{agreement_id}-{line_id:04d}"
        return [line]

    return _items


@pytest.fixture()
def order_factory(
    agreement,
    order_parameters_factory,
    fulfillment_parameters_factory,
    lines_factory,
    status="Processing",
):
    """
    Marketplace platform order for tests.
    """

    def _order(
        order_id="ORD-0792-5000-2253-4210",
        order_type="Purchase",
        order_parameters=None,
        fulfillment_parameters=None,
        lines=None,
        subscriptions=None,
        external_ids=None,
        status=status,
        template=None,
    ):
        order_parameters = (
            order_parameters_factory() if order_parameters is None else order_parameters
        )
        fulfillment_parameters = (
            fulfillment_parameters_factory()
            if fulfillment_parameters is None
            else fulfillment_parameters
        )

        lines = lines_factory() if lines is None else lines
        subscriptions = [] if subscriptions is None else subscriptions

        order = {
            "id": order_id,
            "error": None,
            "href": "/commerce/orders/ORD-0792-5000-2253-4210",
            "agreement": agreement,
            "authorization": {
                "id": "AUT-1234-4567",
            },
            "type": order_type,
            "status": status,
            "clientReferenceNumber": None,
            "notes": "First order to try",
            "lines": lines,
            "subscriptions": subscriptions,
            "parameters": {
                "fulfillment": fulfillment_parameters,
                "ordering": order_parameters,
            },
            "audit": {
                "created": {
                    "at": "2023-12-14T18:02:16.9359",
                    "by": {"id": "USR-0000-0001"},
                },
                "updated": None,
            },
        }
        if external_ids:
            order["externalIds"] = external_ids
        if template:
            order["template"] = template
        return order

    return _order


@pytest.fixture()
def order(order_factory):
    return order_factory()


@pytest.fixture()
def mock_status_notes():
    return {
        "id": "VIPM001",
        "message": "Order can't be processed. Failure reason: a-reason",
    }


@pytest.fixture()
def webhook(settings):
    return {
        "id": "WH-123-123",
        "criteria": {"product.id": settings.MPT_PRODUCTS_IDS[0]},
    }


@pytest.fixture()
def subscriptions_factory(lines_factory):
    def _subscriptions(
        subscription_id="SUB-1000-2000-3000",
        product_name="Awesome product",
        vendor_subscription_id="a-sub-id",
        start_date=None,
        commitment_date=None,
        lines=None,
    ):
        start_date = (
            start_date.isoformat() if start_date else datetime.now(UTC).isoformat()
        )
        lines = lines_factory() if lines is None else lines
        return [
            {
                "id": subscription_id,
                "name": f"Subscription for {product_name}",
                "parameters": {},
                "externalIds": {
                    "vendor": vendor_subscription_id,
                },
                "lines": lines,
                "startDate": start_date,
                "commitmentDate": commitment_date,
            }
        ]

    return _subscriptions


@pytest.fixture()
def mock_wrap_event():
    return Event("evt-id", "orders", {"id": "ORD-1111-1111-1111"})


@pytest.fixture()
def mock_settings_product_ids():
    return ",".join(settings.MPT_PRODUCTS_IDS)


@pytest.fixture()
def mock_get_order_for_producer(order, order_factory):
    order = order_factory()

    return {
        "data": [order],
        "$meta": {
            "pagination": {
                "offset": 0,
                "limit": 10,
                "total": 1,
            },
        },
    }


@pytest.fixture()
def mock_meta_with_pagination_has_more_pages():
    return {
        "$meta": {
            "pagination": {
                "offset": 0,
                "limit": 10,
                "total": 12,
            },
        },
    }


@pytest.fixture()
def mock_meta_with_pagination_has_no_more_pages():
    return {
        "$meta": {
            "pagination": {
                "offset": 0,
                "limit": 10,
                "total": 4,
            },
        },
    }


@pytest.fixture()
def mock_key_vault_name():
    return "test-key-vault-name"


@pytest.fixture()
def mock_secret_name():
    return "test-secret-name"


@pytest.fixture()
def mock_key_vault_url():
    return "https://test-key-vault-name"


@pytest.fixture()
def mock_initializer_options():
    return {
        "app_config_group": DEFAULT_APP_CONFIG_GROUP,
        "app_config_name": DEFAULT_APP_CONFIG_NAME,
        "django_settings_module": DJANGO_SETTINGS_MODULE,
    }


@pytest.fixture()
def mock_mpt_api_error_payload():
    return {
        "status": "error",
        "title": "Error Title",
        "detail": "Error Detail",
        "traceId": "12345",
        "errors": {
            "error1": "error1",
        },
    }
