from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.causation_entry import CausationEntry, CausationEntryStatus


class AccountingSystemPort(ABC):
    """Posts causación entries to an accounting system.

    Phase 1's only implementation is `InternalAccountingSystem` (posts to ContaFlow's
    own ledger tables). A future `SiigoAccountingSystemPort` implementing this same
    contract is the intended extension point for pushing entries to Siigo Nube's API
    — swap it in at the router's dependency-injection site, no domain/use-case changes.
    """

    @abstractmethod
    async def post_entry(self, entry: CausationEntry) -> CausationEntry: ...

    @abstractmethod
    async def get_entry_status(self, entry_id: UUID) -> CausationEntryStatus: ...
