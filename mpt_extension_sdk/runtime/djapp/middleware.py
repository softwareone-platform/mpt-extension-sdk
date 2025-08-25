from django.conf import settings

from mpt_extension_sdk.mpt_http.base import MPTClient

_CLIENT = None


class MPTClientMiddleware:  # pragma: no cover
    """Middleware to set up MPTClient for each request."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Set up MPTClient for the request."""
        global _CLIENT  # noqa: PLW0603
        if not _CLIENT:
            _CLIENT = MPTClient(
                f"{settings.MPT_API_BASE_URL}/v1/",
                settings.MPT_API_TOKEN,
            )
        request.client = _CLIENT
        return self.get_response(request)
