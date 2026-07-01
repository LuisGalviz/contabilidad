from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

import structlog

from src.domain.entities.causation_entry import CausationEntry, CausationEntryLine
from src.domain.entities.supplier_invoice import InvoiceStatus
from src.domain.ports.accounting_system_port import AccountingSystemPort
from src.domain.repositories.supplier_invoice_repository import SupplierInvoiceRepository

logger = structlog.get_logger()

IVA_DESCONTABLE_ACCOUNT = "240801"
PROVEEDORES_ACCOUNT = "2205"


class InvoiceNotClassifiedError(Exception):
    pass


@dataclass
class GenerateCausationEntriesUseCase:
    invoice_repo: SupplierInvoiceRepository
    accounting_system: AccountingSystemPort

    async def execute(self, invoice_ids: list[UUID]) -> list[CausationEntry]:
        entries: list[CausationEntry] = []
        for invoice_id in invoice_ids:
            invoice = await self.invoice_repo.get_by_id(invoice_id)
            if invoice is None:
                continue
            if invoice.status != InvoiceStatus.CLASSIFIED or not invoice.final_account_code:
                raise InvoiceNotClassifiedError(
                    f"Invoice {invoice_id} must be CLASSIFIED with a final account before causación"
                )

            lines = [
                CausationEntryLine(
                    account_code=invoice.final_account_code,
                    debit=invoice.subtotal,
                    credit=Decimal("0"),
                    description=f"{invoice.supplier_name} - {invoice.concept_description}"[:255],
                    cost_center_id=invoice.final_cost_center_id,
                )
            ]
            if invoice.vat_amount > 0:
                lines.append(
                    CausationEntryLine(
                        account_code=IVA_DESCONTABLE_ACCOUNT,
                        debit=invoice.vat_amount,
                        credit=Decimal("0"),
                        description="IVA descontable",
                    )
                )
            lines.append(
                CausationEntryLine(
                    account_code=PROVEEDORES_ACCOUNT,
                    debit=Decimal("0"),
                    credit=invoice.total_amount,
                    description=f"Cuenta por pagar - {invoice.supplier_name}",
                )
            )

            entry = CausationEntry(
                tenant_id=invoice.tenant_id,
                client_id=invoice.client_id,
                invoice_id=invoice.id,
                entry_date=invoice.issue_date,
                lines=lines,
            )
            posted = await self.accounting_system.post_entry(entry)
            invoice.mark_caused()
            await self.invoice_repo.save(invoice)
            entries.append(posted)
            logger.info("causation_entry_posted", entry_id=str(posted.id), invoice_id=str(invoice.id))

        return entries
