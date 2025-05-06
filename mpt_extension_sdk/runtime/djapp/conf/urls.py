from django.contrib import admin
from django.urls import path

from mpt_extension_sdk.constants import (
    DEFAULT_APP_CONFIG_GROUP,
    DEFAULT_APP_CONFIG_NAME,
)
from mpt_extension_sdk.runtime.utils import get_extension

urlpatterns = [
    path("admin/", admin.site.urls),
]

if (
    extension := get_extension(
        name=DEFAULT_APP_CONFIG_NAME, group=DEFAULT_APP_CONFIG_GROUP
    )
) and (api_urls := extension.api.urls):
    urlpatterns.append(path("api/", api_urls))
