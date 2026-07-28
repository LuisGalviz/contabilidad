from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.application.use_cases.purchases.generate_causation_entries import (
    GenerateCausationEntriesUseCase,
    MissingAccountSettingError,
)
from src.domain.entities.causation_entry import CausationEntry
from src.domain.entities.client_account_setting import AccountRole
from src.domain.entities.supplier_invoice import InvoiceStatus, SupplierInvoice

TENANT = uuid4()
CLIENT = uuid4()


def _invoice(**overrides: object) -> SupplierInvoice:
    invoice = SupplierInvoice(
        tenant_id=TENANT,
        client_id=CLIENT,
        import_batch_id=uuid4(),
        cufe="CUFE-1",
        supplier_nit="900111",
        supplier_name="Proveedor SAS",
        issue_date=date(2026, 1, 15),
        concept_description="Servicio de aseo",
        subtotal=Decimal("100000"),
        vat_amount=Decimal("19000"),
        total_amount=Decimal("119000"),
    )
    invoice.status = InvoiceStatus.CLASSIFIED
    invoice.final_account_code = "5135"
    for key, value in overrides.items():
        setattr(invoice, key, value)
    return invoice


class FakeInvoiceRepo:
    def __init__(self, *invoices: SupplierInvoice) -> None:
        self._by_id = {invoice.id: invoice for invoice in invoices}

    async def get_by_id(self, invoice_id: UUID) -> SupplierInvoice | None:
        return self._by_id.get(invoice_id)

    async def save(self, invoice: SupplierInvoice) -> SupplierInvoice:
        return invoice


class FakeAccountingSystem:
    async def post_entry(self, entry: CausationEntry, invoice: SupplierInvoice) -> CausationEntry:
        return entry


class FakeSettingRepo:
    def __init__(self, codes: dict[AccountRole, str]) -> None:
        self._codes = codes
        self.calls = 0

    async def get_codes_by_role(self, tenant_id: UUID, client_id: UUID) -> dict[AccountRole, str]:
        self.calls += 1
        return self._codes


def _use_case(invoice: SupplierInvoice, codes: dict[AccountRole, str]) -> GenerateCausationEntriesUseCase:
    return GenerateCausationEntriesUseCase(
        invoice_repo=FakeInvoiceRepo(invoice),  # type: ignore[arg-type]
        accounting_system=FakeAccountingSystem(),  # type: ignore[arg-type]
        account_setting_repo=FakeSettingRepo(codes),  # type: ignore[arg-type]
    )


class TestCausationUsesClientAccounts:
    @pytest.mark.asyncio
    async def test_uses_the_codes_configured_for_the_client(self):
        invoice = _invoice()
        use_case = _use_case(
            invoice,
            {AccountRole.ACCOUNTS_PAYABLE: "220501", AccountRole.VAT_DEDUCTIBLE: "24081001"},
        )

        entries = await use_case.execute([invoice.id])

        codes = {line.account_code for line in entries[0].lines}
        # Los códigos de la empresa, no los del decreto quemados en el código.
        assert codes == {"5135", "24081001", "220501"}
        assert entries[0].is_balanced()

    @pytest.mark.asyncio
    async def test_fails_loudly_when_a_role_is_not_configured(self):
        invoice = _invoice()
        use_case = _use_case(invoice, {AccountRole.VAT_DEDUCTIBLE: "240801"})

        # Sin cuenta de proveedores, inventar un código produciría un asiento
        # contra la cuenta equivocada. Preferimos no causar.
        with pytest.raises(MissingAccountSettingError):
            await use_case.execute([invoice.id])

    @pytest.mark.asyncio
    async def test_settings_are_read_once_per_client_not_per_invoice(self):
        invoices = [_invoice(cufe=f"CUFE-{n}") for n in range(3)]
        setting_repo = FakeSettingRepo(
            {AccountRole.ACCOUNTS_PAYABLE: "2205", AccountRole.VAT_DEDUCTIBLE: "240801"}
        )
        use_case = GenerateCausationEntriesUseCase(
            invoice_repo=FakeInvoiceRepo(*invoices),  # type: ignore[arg-type]
            accounting_system=FakeAccountingSystem(),  # type: ignore[arg-type]
            account_setting_repo=setting_repo,  # type: ignore[arg-type]
        )

        entries = await use_case.execute([inv.id for inv in invoices])

        # Un lote de causación es de un solo cliente: una consulta, no una por
        # factura.
        assert len(entries) == 3
        assert setting_repo.calls == 1

    @pytest.mark.asyncio
    async def test_credit_note_still_inverts_with_configured_accounts(self):
        invoice = _invoice(is_credit_note=True)
        use_case = _use_case(
            invoice, {AccountRole.ACCOUNTS_PAYABLE: "220501", AccountRole.VAT_DEDUCTIBLE: "24081001"}
        )

        entries = await use_case.execute([invoice.id])

        lines = {line.account_code: line for line in entries[0].lines}
        assert lines["220501"].debit == Decimal("119000")
        assert lines["5135"].credit == Decimal("100000")
        assert entries[0].is_balanced()
