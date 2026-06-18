from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from src.domain.entities.client import Client
from src.domain.repositories.base import BaseRepository


class ClientRepository(BaseRepository[Client]):
    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID, active_only: bool = True) -> list[Client]: ...

    @abstractmethod
    async def nit_exists_in_tenant(self, nit: str, tenant_id: UUID) -> bool: ...

    @abstractmethod
    async def count_by_tenant(self, tenant_id: UUID) -> int: ...
