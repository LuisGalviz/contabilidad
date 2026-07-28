from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

import structlog

from src.infrastructure.siigo.errors import SiigoApiError, SiigoAuthenticationError

if TYPE_CHECKING:
    import httpx

logger = structlog.get_logger()

# Renew the token this many seconds before Siigo's reported expiry (24h)
# so in-flight requests never race an expiring token.
_EXPIRY_MARGIN_SECONDS = 300


class SiigoAuthenticator:
    """Obtains and caches the Siigo JWT (POST /auth, valid 24h).

    Safe for concurrent use: a lock ensures only one refresh happens at a
    time; callers awaiting during a refresh reuse the fresh token.
    """

    def __init__(self, api_url: str, username: str, access_key: str, partner_id: str) -> None:
        self._api_url = api_url.rstrip("/")
        self._username = username
        self._access_key = access_key
        self._partner_id = partner_id
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def get_token(self, client: httpx.AsyncClient) -> str:
        if self._token and time.monotonic() < self._expires_at:
            return self._token

        async with self._lock:
            if self._token and time.monotonic() < self._expires_at:
                return self._token

            response = await client.post(
                f"{self._api_url}/auth",
                json={"username": self._username, "access_key": self._access_key},
                headers={"Partner-Id": self._partner_id},
            )
            if response.status_code in (401, 403):
                raise SiigoAuthenticationError("Siigo rejected the API credentials (username/access_key).")
            if response.status_code >= 400:
                raise SiigoApiError(response.status_code, response.text[:500])

            payload = response.json()
            token = payload.get("access_token")
            if not isinstance(token, str) or not token:
                raise SiigoAuthenticationError("Siigo /auth response did not include an access_token.")

            expires_in = int(payload.get("expires_in", 86400))
            self._token = token
            self._expires_at = time.monotonic() + max(expires_in - _EXPIRY_MARGIN_SECONDS, 60)
            logger.info("siigo_token_refreshed", expires_in=expires_in)
            return token

    def invalidate(self) -> None:
        self._token = None
        self._expires_at = 0.0
