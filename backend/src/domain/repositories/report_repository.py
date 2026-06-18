from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from src.domain.entities.report import Report, ReportType
from src.domain.repositories.base import BaseRepository


class ReportRepository(BaseRepository[Report]):
    @abstractmethod
    async def list_by_client(
        self,
        client_id: UUID,
        tenant_id: UUID,
        report_type: ReportType | None = None,
    ) -> list[Report]: ...

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Report]: ...
