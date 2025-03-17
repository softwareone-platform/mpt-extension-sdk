from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from mpt_extension_sdk.core.extension import Extension

ext = Extension()


class DjAppConfig(AppConfig):
    name = "mpt_extension_sdk.runtime.djapp"

    def ready(self):
        if not hasattr(settings, "MPT_PRODUCTS_IDS") or not settings.MPT_PRODUCTS_IDS:
            raise ImproperlyConfigured(
                f"Extension {self.verbose_name} is not properly configured."
                "MPT_PRODUCTS_IDS is missing or empty."
            )

        self.extension_ready()

    def extension_ready(self):
        pass


class ExtensionConfig(DjAppConfig):
    name = "mpt_extension_sdk"
    verbose_name = "SWO Extension SDK"
    extension = ext

    def extension_ready(self):
        error_msgs = []

        for product_id in settings.MPT_PRODUCTS_IDS:
            if (
                "WEBHOOKS_SECRETS" not in settings.EXTENSION_CONFIG
                or product_id not in settings.EXTENSION_CONFIG["WEBHOOKS_SECRETS"]
            ):
                msg = (
                    f"The webhook secret for {product_id} is not found. "
                    f"Please, specify it in EXT_WEBHOOKS_SECRETS environment variable."
                )
                error_msgs.append(msg)

        if error_msgs:
            raise ImproperlyConfigured("\n".join(error_msgs))
