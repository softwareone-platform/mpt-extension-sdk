import warnings
from urllib.parse import urljoin, urlsplit

from requests import Session
from requests.adapters import HTTPAdapter, Retry

from mpt_extension_sdk.constants import POOL_MAX_SIZE, USER_AGENT


class MPTClient(Session):
    """Client for interacting with the MPT API."""

    _api_version = "public/v1/"

    def __init__(self, base_url, api_token):
        super().__init__()
        retries = Retry(
            total=5,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504],
        )
        self.mount(
            "http://",
            HTTPAdapter(
                max_retries=retries,
                pool_maxsize=POOL_MAX_SIZE,
            ),
        )
        self.mount(
            "https://",
            HTTPAdapter(
                max_retries=retries,
                pool_maxsize=POOL_MAX_SIZE,
            ),
        )
        self.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Authorization": f"Bearer {api_token}",
            },
        )
        self.base_url = urljoin(self._sanitize(base_url), self._api_version)
        self.api_token = api_token

    def request(self, method, url, *args, **kwargs):
        """Send a request to the API."""
        url = self.join_url(url)
        return super().request(method, url, *args, **kwargs)

    def prepare_request(self, request, *args, **kwargs):
        """Prepare the request by joining the base URL."""
        request.url = self.join_url(request.url)
        return super().prepare_request(request, *args, **kwargs)

    def join_url(self, url):
        """Join the base URL with the given URL."""
        url = url[1:] if url[0] == "/" else url
        return urljoin(self.base_url, url)

    def _sanitize(self, base_url):
        """Clean the base URL by removing version paths.

        Args:
            base_url: The base URL which may contain legacy version paths.

        Returns:
            Cleaned base URL without version paths.
        """
        url_parsed = urlsplit(base_url)
        # Support old base url definitions with /public/v1
        if url_parsed.path not in {"", "/"}:
            warnings.warn(
                f"Including {url_parsed.path} in MPT_API_BASE_URL is deprecated. Please use the "
                f"base URL without version path (e.g., 'https://api.platform.softwareone.com'). "
                "The client will automatically append '/public/v1/'.",
                DeprecationWarning,
                stacklevel=3,
            )

        return urlsplit(f"//{url_parsed.netloc}", scheme=url_parsed.scheme).geturl()
