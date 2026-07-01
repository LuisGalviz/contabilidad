from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.ports.accounting_system_port import AccountingSystemPort

if TYPE_CHECKING:
    from uuid import UUID

    from src.domain.entities.causation_entry import CausationEntry, CausationEntryStatus
    from src.domain.repositories.causation_entry_repository import CausationEntryRepository


class InternalAccountingSystem(AccountingSystemPort):
    """Phase 1's only `AccountingSystemPort` implementation: posts to ContaFlow's
    own ledger tables instead of an external system. A future
    `SiigoAccountingSystemPort` (pushing to Siigo Nube's
    `POST /v1/purchase-support-documents`) implements this same contract —
    swap it in at the router's dependency-injection site.
    """

    def __init__(self, causation_repo: CausationEntryRepository) -> None:
        self._causation_repo = causation_repo

    async def post_entry(self, entry: CausationEntry) -> CausationEntry:
        if not entry.is_balanced():
            entry.mark_failed()
            await self._causation_repo.save(entry)
            raise ValueError(f"Causation entry {entry.id} is not balanced (debit != credit).")

        entry.mark_posted()
        await self._causation_repo.save(entry)
        return entry

    async def get_entry_status(self, entry_id: UUID) -> CausationEntryStatus:
        entry = await self._causation_repo.get_by_id(entry_id)
        if entry is None:
            raise ValueError(f"Causation entry {entry_id} not found.")
        return entry.status
