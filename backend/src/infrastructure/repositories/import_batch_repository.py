from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.invoice_import_batch import ImportBatchStatus, InvoiceImportBatch
from src.domain.repositories.import_batch_repository import InvoiceImportBatchRepository
from src.infrastructure.database.models import InvoiceImportBatchModel


class SQLInvoiceImportBatchRepository(InvoiceImportBatchRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> InvoiceImportBatch | None:
        row = await self._session.get(InvoiceImportBatchModel, id)
        return _to_domain(row) if row else None

    async def list_by_tenant(self, tenant_id: UUID, limit: int = 20, offset: int = 0) -> list[InvoiceImportBatch]:
        result = await self._session.execute(
            select(InvoiceImportBatchModel)
            .where(InvoiceImportBatchModel.tenant_id == tenant_id)
            .order_by(InvoiceImportBatchModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [_to_domain(row) for row in result.scalars()]

    async def save(self, batch: InvoiceImportBatch) -> InvoiceImportBatch:
        existing = await self._session.get(InvoiceImportBatchModel, batch.id)
        if existing:
            existing.status = batch.status.value
            existing.total_rows = batch.total_rows
            existing.new_invoices = batch.new_invoices
            existing.duplicate_invoices = batch.duplicate_invoices
            existing.error_rows = batch.error_rows
            existing.error_message = batch.error_message
            existing.updated_at = batch.updated_at
            await self._session.flush()
            return batch

        model = InvoiceImportBatchModel(
            id=batch.id,
            tenant_id=batch.tenant_id,
            client_id=batch.client_id,
            uploaded_by=batch.uploaded_by,
            source_file_key=batch.source_file_key,
            original_name=batch.original_name,
            status=batch.status.value,
            total_rows=batch.total_rows,
            new_invoices=batch.new_invoices,
            duplicate_invoices=batch.duplicate_invoices,
            error_rows=batch.error_rows,
            error_message=batch.error_message,
            created_at=batch.created_at,
            updated_at=batch.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return batch

    async def delete(self, id: UUID) -> None:
        row = await self._session.get(InvoiceImportBatchModel, id)
        if row:
            await self._session.delete(row)
            await self._session.flush()


def _to_domain(model: InvoiceImportBatchModel) -> InvoiceImportBatch:
    return InvoiceImportBatch(
        id=model.id,
        tenant_id=model.tenant_id,
        client_id=model.client_id,
        uploaded_by=model.uploaded_by,
        source_file_key=model.source_file_key,
        original_name=model.original_name,
        status=ImportBatchStatus(model.status),
        total_rows=model.total_rows,
        new_invoices=model.new_invoices,
        duplicate_invoices=model.duplicate_invoices,
        error_rows=model.error_rows,
        error_message=model.error_message,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
