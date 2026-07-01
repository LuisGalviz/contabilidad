from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from src.domain.entities.causation_entry import CausationEntry
from src.domain.repositories.base import BaseRepository


class CausationEntryRepository(BaseRepository[CausationEntry]):
    @abstractmethod
    async def list_by_client(self, tenant_id: UUID, client_id: UUID, period: str | None = None) -> list[CausationEntry]: ...

    @abstractmethod
    async def list_by_client_and_period(
        self,
        tenant_id: UUID,
        client_id: UUID,
        period: str,
    ) -> list[CausationEntry]: ...
