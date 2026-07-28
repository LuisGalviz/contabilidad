from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

import structlog

from src.domain.entities.causation_entry import CausationEntry, CausationEntryLine
from src.domain.entities.client_account_setting import AccountRole
from src.domain.entities.supplier_invoice import InvoiceStatus
from src.domain.ports.accounting_system_port import AccountingSystemPort
from src.domain.repositories.client_account_setting_repository import ClientAccountSettingRepository
from src.domain.repositories.supplier_invoice_repository import SupplierInvoiceRepository

logger = structlog.get_logger()


class InvoiceNotClassifiedError(Exception):
    pass


class MissingAccountSettingError(Exception):
    """Al cliente le falta configurar qué cuenta usa para un papel de la
    causación. Preferimos fallar antes que inventar un código: un asiento
    contra una cuenta equivocada es peor que no causar."""


@dataclass
class GenerateCausationEntriesUseCase:
    invoice_repo: SupplierInvoiceRepository
    accounting_system: AccountingSystemPort
    account_setting_repo: ClientAccountSettingRepository
    _settings_cache: dict[UUID, dict[AccountRole, str]] = field(default_factory=dict, init=False)

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

            payable_account = await self._account_for(invoice.tenant_id, invoice.client_id, AccountRole.ACCOUNTS_PAYABLE)

            # A normal purchase debits the expense/IVA and credits proveedores.
            # A credit note reverses the purchase, so every side flips: the
            # expense/IVA are credited and proveedores is debited.
            zero = Decimal("0")
            nc = invoice.is_credit_note
            nc_tag = " (nota crédito)" if nc else ""

            lines = [
                CausationEntryLine(
                    account_code=invoice.final_account_code,
                    debit=zero if nc else invoice.subtotal,
                    credit=invoice.subtotal if nc else zero,
                    description=f"{invoice.supplier_name} - {invoice.concept_description}{nc_tag}"[:255],
                    cost_center_id=invoice.final_cost_center_id,
                )
            ]
            if invoice.vat_amount > 0:
                vat_account = await self._account_for(invoice.tenant_id, invoice.client_id, AccountRole.VAT_DEDUCTIBLE)
                lines.append(
                    CausationEntryLine(
                        account_code=vat_account,
                        debit=zero if nc else invoice.vat_amount,
                        credit=invoice.vat_amount if nc else zero,
                        description=f"IVA descontable{nc_tag}",
                    )
                )
            lines.append(
                CausationEntryLine(
                    account_code=payable_account,
                    debit=invoice.total_amount if nc else zero,
                    credit=zero if nc else invoice.total_amount,
                    description=f"Cuenta por pagar - {invoice.supplier_name}{nc_tag}",
                )
            )

            entry = CausationEntry(
                tenant_id=invoice.tenant_id,
                client_id=invoice.client_id,
                invoice_id=invoice.id,
                entry_date=invoice.issue_date,
                lines=lines,
            )
            posted = await self.accounting_system.post_entry(entry, invoice)
            invoice.mark_caused()
            await self.invoice_repo.save(invoice)
            entries.append(posted)
            logger.info("causation_entry_posted", entry_id=str(posted.id), invoice_id=str(invoice.id))

        return entries

    async def _account_for(self, tenant_id: UUID, client_id: UUID, role: AccountRole) -> str:
        """Resuelve el código configurado para un papel. Cachea por cliente: un
        lote de causación es de un solo cliente, así que es una consulta y no
        una por factura."""
        codes = self._settings_cache.get(client_id)
        if codes is None:
            codes = await self.account_setting_repo.get_codes_by_role(tenant_id, client_id)
            self._settings_cache[client_id] = codes

        code = codes.get(role)
        if not code:
            raise MissingAccountSettingError(
                f"El cliente {client_id} no tiene configurada la cuenta para '{role.value}'. "
                "Defínela en la configuración contable del cliente antes de causar."
            )
        return code
