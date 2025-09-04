from mpt_extension_sdk.constants import (
    DEFAULT_APP_CONFIG_GROUP,
    DEFAULT_APP_CONFIG_NAME,
)
from mpt_extension_sdk.runtime.utils import get_extension, get_urlpatterns

extension = get_extension(name=DEFAULT_APP_CONFIG_NAME, group=DEFAULT_APP_CONFIG_GROUP)

urlpatterns = get_urlpatterns(extension)
