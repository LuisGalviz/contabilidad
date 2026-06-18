from __future__ import annotations

from abc import abstractmethod

from src.domain.entities.tenant import Tenant
from src.domain.repositories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    @abstractmethod
    async def get_by_slug(self, slug: str) -> Tenant | None: ...

    @abstractmethod
    async def slug_exists(self, slug: str) -> bool: ...

    @abstractmethod
    async def list_all(self, limit: int = 50, offset: int = 0) -> list[Tenant]: ...
