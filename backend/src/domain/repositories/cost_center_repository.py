from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from src.domain.entities.cost_center import CostCenter
from src.domain.repositories.base import BaseRepository


class CostCenterRepository(BaseRepository[CostCenter]):
    @abstractmethod
    async def list_by_client(self, tenant_id: UUID, client_id: UUID, active_only: bool = True) -> list[CostCenter]: ...
