from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from src.config import get_settings
from src.infrastructure.accounting.internal_accounting_system import InternalAccountingSystem
from src.infrastructure.siigo.accounting_system import SiigoAccountingSystem
from src.infrastructure.siigo.auth import SiigoAuthenticator
from src.infrastructure.siigo.client import SiigoHttpClient
from src.infrastructure.siigo.errors import SiigoConfigurationError
from src.infrastructure.siigo.mock_client import MockSiigoClient

if TYPE_CHECKING:
    from src.domain.ports.accounting_system_port import AccountingSystemPort
    from src.domain.repositories.causation_entry_repository import CausationEntryRepository
    from src.infrastructure.siigo.client import SiigoClient


@lru_cache
def _shared_siigo_client() -> SiigoClient:
    """One client per process so the 24h Siigo token is fetched once, not per
    request. Cached only when Siigo is enabled with real credentials."""
    settings = get_settings()
    if not settings.siigo_username or not settings.siigo_access_key:
        raise SiigoConfigurationError(
            "SIIGO_ENABLED=true with SIIGO_USE_MOCK=false requires SIIGO_USERNAME and SIIGO_ACCESS_KEY."
        )
    if settings.siigo_journal_document_id <= 0:
        raise SiigoConfigurationError(
            "SIIGO_JOURNAL_DOCUMENT_ID must be set to the Siigo document-type id for comprobantes "
            "de contabilidad (see GET /v1/document-types?type=CC)."
        )
    authenticator = SiigoAuthenticator(
        api_url=settings.siigo_api_url,
        username=settings.siigo_username,
        access_key=settings.siigo_access_key,
        partner_id=settings.siigo_partner_id,
    )
    return SiigoHttpClient(settings.siigo_api_url, settings.siigo_partner_id, authenticator)


@lru_cache
def _shared_mock_client() -> MockSiigoClient:
    """Shared so pushed journals accumulate across requests within a process,
    which makes local inspection easier."""
    return MockSiigoClient()


def build_accounting_system(causation_repo: CausationEntryRepository) -> AccountingSystemPort:
    """Dependency-injection site for `AccountingSystemPort`: returns the Siigo
    implementation when SIIGO_ENABLED=true (mock or real per SIIGO_USE_MOCK),
    otherwise ContaFlow's internal ledger.
    """
    settings = get_settings()
    if not settings.siigo_enabled:
        return InternalAccountingSystem(causation_repo)

    client: SiigoClient = _shared_mock_client() if settings.siigo_use_mock else _shared_siigo_client()
    return SiigoAccountingSystem(causation_repo, client, settings.siigo_journal_document_id)
