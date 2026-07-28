from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx
import structlog
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from src.infrastructure.siigo.errors import SiigoApiError

if TYPE_CHECKING:
    from src.infrastructure.siigo.auth import SiigoAuthenticator

logger = structlog.get_logger()

_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class SiigoJournalResult:
    """Outcome of creating a journal entry (comprobante contable) in Siigo."""

    siigo_id: str
    document_number: str | None = None


class SiigoClient(ABC):
    """Minimal Siigo API surface ContaFlow depends on.

    Implementations: `SiigoHttpClient` (real API) and `MockSiigoClient`
    (development without credentials).
    """

    @abstractmethod
    async def create_journal(self, payload: dict[str, Any]) -> SiigoJournalResult: ...

    @abstractmethod
    async def create_purchase(self, payload: dict[str, Any]) -> SiigoJournalResult:
        """Factura de compra (POST /v1/purchases). A diferencia del journal,
        Siigo deriva impuestos y cuenta por pagar con sus propias reglas."""


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    # 401 is retryable because the request path invalidates the cached token
    # before raising, so the next attempt re-authenticates.
    return isinstance(exc, SiigoApiError) and (
        exc.status_code in (401, 429) or exc.status_code >= 500
    )


class SiigoHttpClient(SiigoClient):
    """Real Siigo Nube API client (https://api.siigo.com).

    Sends the mandatory `Partner-Id` header on every request and retries
    transient failures (network errors, 429, 5xx) with exponential backoff.
    """

    def __init__(self, api_url: str, partner_id: str, authenticator: SiigoAuthenticator) -> None:
        self._api_url = api_url.rstrip("/")
        self._partner_id = partner_id
        self._auth = authenticator

    async def create_journal(self, payload: dict[str, Any]) -> SiigoJournalResult:
        data = await self._request("POST", "/v1/journals", payload)
        siigo_id = str(data.get("id", ""))
        if not siigo_id:
            raise SiigoApiError(502, "Siigo journal response did not include an id.")
        number = data.get("number") or data.get("name")
        return SiigoJournalResult(siigo_id=siigo_id, document_number=str(number) if number else None)

    async def create_purchase(self, payload: dict[str, Any]) -> SiigoJournalResult:
        data = await self._request("POST", "/v1/purchases", payload)
        siigo_id = str(data.get("id", ""))
        if not siigo_id:
            raise SiigoApiError(502, "Siigo purchase response did not include an id.")
        number = data.get("number") or data.get("name")
        return SiigoJournalResult(siigo_id=siigo_id, document_number=str(number) if number else None)

    async def _request(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception(_is_retryable),
                wait=wait_exponential(multiplier=1, max=30),
                stop=stop_after_attempt(4),
                reraise=True,
            ):
                with attempt:
                    token = await self._auth.get_token(client)
                    response = await client.request(
                        method,
                        f"{self._api_url}{path}",
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Partner-Id": self._partner_id,
                        },
                    )
                    if response.status_code == 401:
                        # Token may have been revoked server-side; force refresh and retry.
                        self._auth.invalidate()
                        raise SiigoApiError(response.status_code, response.text[:500])
                    if response.status_code >= 400:
                        raise SiigoApiError(response.status_code, response.text[:500])
                    result: dict[str, Any] = response.json()
                    return result
        raise SiigoApiError(500, "Siigo request retries exhausted.")  # pragma: no cover
