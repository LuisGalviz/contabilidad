from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from src.domain.entities.puc_account import PUCAccount
from src.domain.repositories.base import BaseRepository


class PUCAccountRepository(BaseRepository[PUCAccount]):
    """Todas las consultas van acotadas por cliente: el plan de cuentas es de
    la empresa, no del sistema."""

    @abstractmethod
    async def get_by_code(self, tenant_id: UUID, client_id: UUID, code: str) -> PUCAccount | None: ...

    @abstractmethod
    async def list_active(
        self,
        tenant_id: UUID,
        client_id: UUID,
        account_class: str | None = None,
        search: str | None = None,
    ) -> list[PUCAccount]: ...

    @abstractmethod
    async def save_many(self, accounts: list[PUCAccount]) -> int:
        """Alta masiva para sembrar el plan de un cliente nuevo. Devuelve
        cuántas cuentas quedaron escritas."""
