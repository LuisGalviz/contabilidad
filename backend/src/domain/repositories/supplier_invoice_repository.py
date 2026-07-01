from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from src.domain.entities.supplier_invoice import InvoiceStatus, SupplierInvoice
from src.domain.repositories.base import BaseRepository


class SupplierInvoiceRepository(BaseRepository[SupplierInvoice]):
    @abstractmethod
    async def exists_by_cufe(self, tenant_id: UUID, client_id: UUID, cufe: str) -> bool: ...

    @abstractmethod
    async def save_many(self, invoices: list[SupplierInvoice]) -> list[SupplierInvoice]: ...

    @abstractmethod
    async def list_by_batch(self, import_batch_id: UUID) -> list[SupplierInvoice]: ...

    @abstractmethod
    async def list_by_client(
        self,
        tenant_id: UUID,
        client_id: UUID,
        status: InvoiceStatus | None = None,
    ) -> list[SupplierInvoice]: ...

    @abstractmethod
    async def list_by_client_and_period(
        self,
        tenant_id: UUID,
        client_id: UUID,
        period: str,
    ) -> list[SupplierInvoice]: ...
