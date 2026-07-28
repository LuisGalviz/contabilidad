from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from src.domain.entities.causation_entry import CausationEntry, CausationEntryLine
from src.domain.entities.supplier_invoice import SupplierInvoice
from src.infrastructure.siigo.accounting_system import (
    DOCUMENT_MODE_PURCHASES,
    SiigoAccountingSystem,
)
from src.infrastructure.siigo.mapper import causation_entry_to_purchase_payload
from src.infrastructure.siigo.mock_client import MockSiigoClient


def _invoice(**overrides: object) -> SupplierInvoice:
    invoice = SupplierInvoice(
        tenant_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        import_batch_id=uuid.uuid4(),
        cufe="CUFE-ABC",
        supplier_nit="900111",
        supplier_name="Proveedor SAS",
        issue_date=date(2026, 1, 15),
        concept_description="Servicio de aseo",
        subtotal=Decimal("100000"),
        vat_amount=Decimal("19000"),
        total_amount=Decimal("119000"),
        document_prefix="FE",
        document_number="1234",
    )
    invoice.final_account_code = "5135"
    for key, value in overrides.items():
        setattr(invoice, key, value)
    return invoice


def _entry(invoice: SupplierInvoice) -> CausationEntry:
    return CausationEntry(
        tenant_id=invoice.tenant_id,
        client_id=invoice.client_id,
        invoice_id=invoice.id,
        entry_date=invoice.issue_date,
        lines=[
            CausationEntryLine(
                account_code="5135", debit=Decimal("100000"), credit=Decimal("0"), description="Aseo"
            ),
            CausationEntryLine(
                account_code="240801", debit=Decimal("19000"), credit=Decimal("0"), description="IVA"
            ),
            CausationEntryLine(
                account_code="2205", debit=Decimal("0"), credit=Decimal("119000"), description="CxP"
            ),
        ],
    )


class _FakeRepo:
    async def save(self, entry: CausationEntry) -> CausationEntry:
        return entry

    async def get_by_id(self, entry_id: uuid.UUID) -> CausationEntry | None:
        return None


class TestPurchasePayload:
    def test_sends_only_expense_lines_because_siigo_derives_the_rest(self):
        invoice = _invoice()

        payload = causation_entry_to_purchase_payload(_entry(invoice), invoice, document_id=7, payment_type_id=3)

        # El IVA y la cuenta por pagar los calcula Siigo con sus propias reglas;
        # mandarlos como ítems los duplicaría.
        assert [item["code"] for item in payload["items"]] == ["5135"]
        assert payload["items"][0]["type"] == "Account"
        assert payload["items"][0]["price"] == 100000.0

    def test_carries_supplier_and_provider_invoice(self):
        invoice = _invoice()

        payload = causation_entry_to_purchase_payload(_entry(invoice), invoice, document_id=7, payment_type_id=3)

        assert payload["supplier"] == {"identification": "900111"}
        assert payload["provider_invoice"] == {"prefix": "FE", "number": "1234"}
        assert payload["payments"] == [{"id": 3, "value": 119000.0}]

    def test_omits_provider_invoice_when_the_dian_file_had_no_number(self):
        invoice = _invoice(document_prefix="", document_number="")

        payload = causation_entry_to_purchase_payload(_entry(invoice), invoice, document_id=7, payment_type_id=3)

        # Siigo rechaza `provider_invoice` incompleto: mejor no mandarlo.
        assert "provider_invoice" not in payload

    def test_keeps_the_cufe_traceable_in_observations(self):
        invoice = _invoice()

        payload = causation_entry_to_purchase_payload(_entry(invoice), invoice, document_id=7, payment_type_id=3)

        assert "CUFE-ABC" in payload["observations"]


class TestPurchaseMode:
    @pytest.mark.asyncio
    async def test_purchase_mode_hits_the_purchases_endpoint(self):
        client = MockSiigoClient()
        system = SiigoAccountingSystem(
            _FakeRepo(),  # type: ignore[arg-type]
            client,
            journal_document_id=7,
            document_mode=DOCUMENT_MODE_PURCHASES,
            payment_type_id=3,
        )
        invoice = _invoice()

        entry = await system.post_entry(_entry(invoice), invoice)

        assert len(client.purchases) == 1
        assert client.journals == []
        assert entry.external_reference is not None and entry.external_reference.startswith("siigo:")

    @pytest.mark.asyncio
    async def test_default_mode_still_uses_journals(self):
        client = MockSiigoClient()
        system = SiigoAccountingSystem(_FakeRepo(), client, journal_document_id=7)  # type: ignore[arg-type]
        invoice = _invoice()

        await system.post_entry(_entry(invoice), invoice)

        assert len(client.journals) == 1
        assert client.purchases == []
