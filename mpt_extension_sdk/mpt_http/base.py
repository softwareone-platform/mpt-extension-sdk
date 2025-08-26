from urllib.parse import urljoin

from requests import Session
from requests.adapters import HTTPAdapter, Retry

from mpt_extension_sdk.constants import POOL_MAX_SIZE, USER_AGENT


class MPTClient(Session):
    """Client for interacting with the MPT API."""
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
        self.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Authorization": f"Bearer {api_token}",
            },
        )
        self.base_url = base_url if base_url[-1] == "/" else f"{base_url}/"
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
