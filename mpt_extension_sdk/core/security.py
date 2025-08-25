import logging
from collections.abc import Callable, Mapping
from typing import Any, ClassVar

import jwt
from django.http import HttpRequest
from ninja.security import HttpBearer

from mpt_extension_sdk.constants import SECURITY_ALGORITHM
from mpt_extension_sdk.mpt_http.base import MPTClient

logger = logging.getLogger(__name__)


class JWTAuth(HttpBearer):
    """JWT authentication using JSON Web Tokens."""
    jwt_algos: ClassVar[list[str]] = [SECURITY_ALGORITHM]

    def __init__(
        self,
        secret_callback: Callable[[MPTClient, Mapping[str, Any]], str],
    ) -> None:
        self.secret_callback = secret_callback
        super().__init__()

    def authenticate(self, request: HttpRequest, token: str) -> Any | None:
        """Authenticate the request using the provided JWT token."""
        try:
            request.jwt_claims = self.get_claims(request, token)
        except jwt.PyJWTError as err:
            logger.exception("Call cannot be authenticated: %r", err)  # noqa: TRY401
        else:
            return request.jwt_claims

    def get_claims(self, request, token):
        """Extract JWT claims from the token."""
        claims = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_aud": False,
            },
            algorithms=self.jwt_algos,
        )
        secret = self.secret_callback(request.client, claims)
        if not secret:
            return None
        jwt.decode(
            token,
            secret,
            options={
                "verify_aud": False,
            },
            algorithms=self.jwt_algos,
        )
        request.jwt_claims = claims
        return claims
