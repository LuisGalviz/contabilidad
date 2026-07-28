from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.domain.ports.accounting_system_port import AccountingSystemPort
from src.infrastructure.siigo.errors import SiigoError
from src.infrastructure.siigo.mapper import causation_entry_to_journal_payload

if TYPE_CHECKING:
    from uuid import UUID

    from src.domain.entities.causation_entry import CausationEntry, CausationEntryStatus
    from src.domain.repositories.causation_entry_repository import CausationEntryRepository
    from src.infrastructure.siigo.client import SiigoClient

logger = structlog.get_logger()


class SiigoAccountingSystem(AccountingSystemPort):
    """`AccountingSystemPort` implementation that pushes causación entries to
    Siigo Nube as journal entries (comprobantes de contabilidad) and records
    Siigo's id as `external_reference`. The entry is also persisted locally,
    same as `InternalAccountingSystem`, so reports keep working unchanged.
    """

    def __init__(
        self,
        causation_repo: CausationEntryRepository,
        siigo_client: SiigoClient,
        journal_document_id: int,
    ) -> None:
        self._causation_repo = causation_repo
        self._siigo = siigo_client
        self._journal_document_id = journal_document_id

    async def post_entry(self, entry: CausationEntry) -> CausationEntry:
        if not entry.is_balanced():
            entry.mark_failed()
            await self._causation_repo.save(entry)
            raise ValueError(f"Causation entry {entry.id} is not balanced (debit != credit).")

        payload = causation_entry_to_journal_payload(entry, self._journal_document_id)
        try:
            result = await self._siigo.create_journal(payload)
        except SiigoError as exc:
            entry.mark_failed()
            await self._causation_repo.save(entry)
            logger.error("siigo_journal_push_failed", entry_id=str(entry.id), error=str(exc))
            raise

        reference = result.document_number or result.siigo_id
        entry.mark_pushed_external(f"siigo:{reference}")
        await self._causation_repo.save(entry)
        logger.info(
            "siigo_journal_pushed",
            entry_id=str(entry.id),
            siigo_id=result.siigo_id,
            document_number=result.document_number,
        )
        return entry

    async def get_entry_status(self, entry_id: UUID) -> CausationEntryStatus:
        entry = await self._causation_repo.get_by_id(entry_id)
        if entry is None:
            raise ValueError(f"Causation entry {entry_id} not found.")
        return entry.status
