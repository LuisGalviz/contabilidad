from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from src.domain.entities.mapping_rule import SupplierMappingRule
from src.domain.repositories.base import BaseRepository


class SupplierMappingRuleRepository(BaseRepository[SupplierMappingRule]):
    @abstractmethod
    async def find_best_match(
        self,
        tenant_id: UUID,
        client_id: UUID,
        supplier_nit: str,
        keywords: list[str],
    ) -> SupplierMappingRule | None: ...

    @abstractmethod
    async def list_by_client(self, tenant_id: UUID, client_id: UUID) -> list[SupplierMappingRule]: ...
