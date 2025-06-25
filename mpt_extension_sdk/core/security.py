import logging
from collections.abc import Callable, Mapping
from typing import Any

import jwt
from django.http import HttpRequest
from ninja.security import HttpBearer

from mpt_extension_sdk.constants import SECURITY_ALGORITHM
from mpt_extension_sdk.mpt_http.base import MPTClient

logger = logging.getLogger(__name__)


class JWTAuth(HttpBearer):
    JWT_ALGOS = [SECURITY_ALGORITHM]

    def __init__(
        self,
        secret_callback: Callable[[MPTClient, Mapping[str, Any]], str],
    ) -> None:
        self.secret_callback = secret_callback
        super().__init__()

    def authenticate(self, request: HttpRequest, token: str) -> Any | None:
        try:
            claims = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_aud": False,
                },
                algorithms=self.JWT_ALGOS,
            )
            secret = self.secret_callback(request.client, claims)
            if not secret:
                return
            jwt.decode(
                token,
                secret,
                options={
                    "verify_aud": False,
                },
                algorithms=self.JWT_ALGOS,
            )
            request.jwt_claims = claims
            return claims

        except jwt.PyJWTError as e:
            logger.error(f"Call cannot be authenticated: {str(e)}")
