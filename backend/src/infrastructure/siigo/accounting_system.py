from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.domain.ports.accounting_system_port import AccountingSystemPort
from src.infrastructure.siigo.errors import SiigoError
from src.infrastructure.siigo.mapper import (
    causation_entry_to_journal_payload,
    causation_entry_to_purchase_payload,
)

if TYPE_CHECKING:
    from uuid import UUID

    from src.domain.entities.causation_entry import CausationEntry, CausationEntryStatus
    from src.domain.entities.supplier_invoice import SupplierInvoice
    from src.domain.repositories.causation_entry_repository import CausationEntryRepository
    from src.infrastructure.siigo.client import SiigoClient

logger = structlog.get_logger()

DOCUMENT_MODE_JOURNALS = "journals"
DOCUMENT_MODE_PURCHASES = "purchases"


class SiigoAccountingSystem(AccountingSystemPort):
    """`AccountingSystemPort` contra Siigo Nube.

    Dos destinos posibles, según `document_mode`:

    - `journals` (`POST /v1/journals`): manda el asiento ya armado. ContaFlow
      decide la contabilización completa.
    - `purchases` (`POST /v1/purchases`): manda la factura y Siigo deriva
      impuestos y cuenta por pagar con sus propias reglas. Es el destino natural
      para compras y el que abre la puerta a retenciones y forma de pago.

    En ambos casos el asiento se persiste local -los informes dependen de
    `causation_entries`- y se guarda la referencia devuelta por Siigo.
    """

    def __init__(
        self,
        causation_repo: CausationEntryRepository,
        siigo_client: SiigoClient,
        journal_document_id: int,
        document_mode: str = DOCUMENT_MODE_JOURNALS,
        payment_type_id: int = 0,
    ) -> None:
        self._causation_repo = causation_repo
        self._siigo = siigo_client
        self._journal_document_id = journal_document_id
        self._document_mode = document_mode
        self._payment_type_id = payment_type_id

    async def post_entry(self, entry: CausationEntry, invoice: SupplierInvoice) -> CausationEntry:
        if not entry.is_balanced():
            entry.mark_failed()
            await self._causation_repo.save(entry)
            raise ValueError(f"Causation entry {entry.id} is not balanced (debit != credit).")

        try:
            if self._document_mode == DOCUMENT_MODE_PURCHASES:
                payload = causation_entry_to_purchase_payload(
                    entry, invoice, self._journal_document_id, self._payment_type_id
                )
                result = await self._siigo.create_purchase(payload)
            else:
                result = await self._siigo.create_journal(
                    causation_entry_to_journal_payload(entry, self._journal_document_id)
                )
        except SiigoError as exc:
            entry.mark_failed()
            await self._causation_repo.save(entry)
            logger.error("siigo_push_failed", entry_id=str(entry.id), mode=self._document_mode, error=str(exc))
            raise

        reference = result.document_number or result.siigo_id
        entry.mark_pushed_external(f"siigo:{reference}")
        await self._causation_repo.save(entry)
        logger.info(
            "siigo_document_pushed",
            entry_id=str(entry.id),
            mode=self._document_mode,
            siigo_id=result.siigo_id,
            document_number=result.document_number,
        )
        return entry

    async def get_entry_status(self, entry_id: UUID) -> CausationEntryStatus:
        entry = await self._causation_repo.get_by_id(entry_id)
        if entry is None:
            raise ValueError(f"Causation entry {entry_id} not found.")
        return entry.status
