from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from src.domain.entities.invoice_import_batch import InvoiceImportBatch
from src.domain.repositories.base import BaseRepository


class InvoiceImportBatchRepository(BaseRepository[InvoiceImportBatch]):
    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID, limit: int = 20, offset: int = 0) -> list[InvoiceImportBatch]: ...
