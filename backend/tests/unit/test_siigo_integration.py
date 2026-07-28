from __future__ import annotations

import json
import uuid
from datetime import date
from decimal import Decimal

import httpx
import pytest

from src.domain.entities.causation_entry import (
    CausationEntry,
    CausationEntryLine,
    CausationEntryStatus,
)
from src.domain.entities.supplier_invoice import SupplierInvoice
from src.infrastructure.siigo.accounting_system import SiigoAccountingSystem
from src.infrastructure.siigo.auth import SiigoAuthenticator
from src.infrastructure.siigo.errors import SiigoApiError, SiigoAuthenticationError, SiigoError
from src.infrastructure.siigo.mapper import causation_entry_to_journal_payload
from src.infrastructure.siigo.mock_client import MockSiigoClient


def _make_entry(lines: list[CausationEntryLine] | None = None) -> CausationEntry:
    return CausationEntry(
        tenant_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        invoice_id=uuid.uuid4(),
        entry_date=date(2026, 1, 15),
        lines=lines
        or [
            CausationEntryLine(account_code="5195", debit=Decimal("100000"), credit=Decimal("0"), description="Gasto"),
            CausationEntryLine(account_code="240801", debit=Decimal("19000"), credit=Decimal("0"), description="IVA"),
            CausationEntryLine(account_code="2205", debit=Decimal("0"), credit=Decimal("119000"), description="CxP"),
        ],
    )


def _make_invoice() -> SupplierInvoice:
    return SupplierInvoice(
        tenant_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        import_batch_id=uuid.uuid4(),
        cufe="CUFE-1",
        supplier_nit="900111",
        supplier_name="Proveedor SAS",
        issue_date=date(2026, 1, 15),
        concept_description="Servicio",
        subtotal=Decimal("100000"),
        vat_amount=Decimal("19000"),
        total_amount=Decimal("119000"),
        document_prefix="FE",
        document_number="1234",
    )


class _FakeCausationRepo:
    def __init__(self) -> None:
        self.saved: list[CausationEntry] = []
        self.entries: dict[uuid.UUID, CausationEntry] = {}

    async def save(self, entry: CausationEntry) -> CausationEntry:
        self.saved.append(entry)
        self.entries[entry.id] = entry
        return entry

    async def get_by_id(self, entry_id: uuid.UUID) -> CausationEntry | None:
        return self.entries.get(entry_id)


class TestJournalMapper:
    def test_maps_lines_to_debit_and_credit_items(self):
        entry = _make_entry()
        payload = causation_entry_to_journal_payload(entry, document_id=27441)

        assert payload["document"] == {"id": 27441}
        assert payload["date"] == "2026-01-15"
        assert len(payload["items"]) == 3

        gasto, iva, cxp = payload["items"]
        assert gasto["account"] == {"code": "5195", "movement": "Debit"}
        assert gasto["value"] == 100000.0
        assert iva["account"] == {"code": "240801", "movement": "Debit"}
        assert cxp["account"] == {"code": "2205", "movement": "Credit"}
        assert cxp["value"] == 119000.0

    def test_observations_reference_entry_and_invoice(self):
        entry = _make_entry()
        payload = causation_entry_to_journal_payload(entry, document_id=1)
        assert str(entry.id) in payload["observations"]
        assert str(entry.invoice_id) in payload["observations"]


class TestSiigoAccountingSystem:
    async def test_pushes_balanced_entry_and_marks_pushed_external(self):
        repo = _FakeCausationRepo()
        mock_client = MockSiigoClient()
        system = SiigoAccountingSystem(repo, mock_client, journal_document_id=1)

        entry = await system.post_entry(_make_entry(), _make_invoice())

        assert entry.status == CausationEntryStatus.PUSHED_EXTERNAL
        assert entry.external_reference is not None
        assert entry.external_reference.startswith("siigo:")
        assert len(mock_client.journals) == 1
        assert repo.saved == [entry]

    async def test_unbalanced_entry_fails_without_calling_siigo(self):
        repo = _FakeCausationRepo()
        mock_client = MockSiigoClient()
        system = SiigoAccountingSystem(repo, mock_client, journal_document_id=1)
        entry = _make_entry(
            [CausationEntryLine(account_code="5195", debit=Decimal("100"), credit=Decimal("0"), description="Gasto")]
        )

        with pytest.raises(ValueError):
            await system.post_entry(entry, _make_invoice())

        assert entry.status == CausationEntryStatus.FAILED
        assert mock_client.journals == []

    async def test_siigo_error_marks_entry_failed(self):
        class _FailingClient(MockSiigoClient):
            async def create_journal(self, payload):  # type: ignore[override]
                raise SiigoApiError(500, "boom")

        repo = _FakeCausationRepo()
        system = SiigoAccountingSystem(repo, _FailingClient(), journal_document_id=1)
        entry = _make_entry()

        with pytest.raises(SiigoError):
            await system.post_entry(entry, _make_invoice())

        assert entry.status == CausationEntryStatus.FAILED
        assert repo.saved == [entry]

    async def test_get_entry_status_reads_from_repo(self):
        repo = _FakeCausationRepo()
        system = SiigoAccountingSystem(repo, MockSiigoClient(), journal_document_id=1)
        entry = await system.post_entry(_make_entry(), _make_invoice())

        assert await system.get_entry_status(entry.id) == CausationEntryStatus.PUSHED_EXTERNAL


class TestSiigoAuthenticator:
    def _client(self, handler) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def test_fetches_and_caches_token(self):
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            assert request.url.path == "/auth"
            assert request.headers["Partner-Id"] == "ContaFlow"
            body = json.loads(request.content)
            assert body == {"username": "user@test.com", "access_key": "key123"}
            return httpx.Response(200, json={"access_token": "jwt-token", "expires_in": 86400})

        auth = SiigoAuthenticator("https://api.siigo.com", "user@test.com", "key123", "ContaFlow")
        async with self._client(handler) as client:
            assert await auth.get_token(client) == "jwt-token"
            assert await auth.get_token(client) == "jwt-token"
        assert calls == 1

    async def test_invalid_credentials_raise_authentication_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "invalid"})

        auth = SiigoAuthenticator("https://api.siigo.com", "user@test.com", "bad", "ContaFlow")
        async with self._client(handler) as client:
            with pytest.raises(SiigoAuthenticationError):
                await auth.get_token(client)

    async def test_invalidate_forces_refresh(self):
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200, json={"access_token": f"jwt-{calls}", "expires_in": 86400})

        auth = SiigoAuthenticator("https://api.siigo.com", "user@test.com", "key123", "ContaFlow")
        async with self._client(handler) as client:
            assert await auth.get_token(client) == "jwt-1"
            auth.invalidate()
            assert await auth.get_token(client) == "jwt-2"
        assert calls == 2
