from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.supplier_invoice import (
    ClassificationSource,
    InvoiceStatus,
    SupplierInvoice,
)
from src.domain.repositories.supplier_invoice_repository import SupplierInvoiceRepository
from src.infrastructure.database.models import SupplierInvoiceModel
from src.infrastructure.purchases.period_utils import period_bounds


class SQLSupplierInvoiceRepository(SupplierInvoiceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> SupplierInvoice | None:
        row = await self._session.get(SupplierInvoiceModel, id)
        return _to_domain(row) if row else None

    async def exists_by_cufe(self, tenant_id: UUID, client_id: UUID, cufe: str) -> bool:
        result = await self._session.execute(
            select(SupplierInvoiceModel.id).where(
                SupplierInvoiceModel.tenant_id == tenant_id,
                SupplierInvoiceModel.client_id == client_id,
                SupplierInvoiceModel.cufe == cufe,
            )
        )
        return result.scalar_one_or_none() is not None

    async def save_many(self, invoices: list[SupplierInvoice]) -> list[SupplierInvoice]:
        for invoice in invoices:
            await self.save(invoice)
        return invoices

    async def list_by_batch(self, import_batch_id: UUID) -> list[SupplierInvoice]:
        result = await self._session.execute(
            select(SupplierInvoiceModel)
            .where(SupplierInvoiceModel.import_batch_id == import_batch_id)
            .order_by(SupplierInvoiceModel.created_at)
        )
        return [_to_domain(row) for row in result.scalars()]

    async def list_by_client(
        self,
        tenant_id: UUID,
        client_id: UUID,
        status: InvoiceStatus | None = None,
    ) -> list[SupplierInvoice]:
        q = select(SupplierInvoiceModel).where(
            SupplierInvoiceModel.tenant_id == tenant_id,
            SupplierInvoiceModel.client_id == client_id,
        )
        if status:
            q = q.where(SupplierInvoiceModel.status == status.value)
        result = await self._session.execute(q.order_by(SupplierInvoiceModel.issue_date.desc()))
        return [_to_domain(row) for row in result.scalars()]

    async def list_by_client_and_period(
        self,
        tenant_id: UUID,
        client_id: UUID,
        period: str,
    ) -> list[SupplierInvoice]:
        start, end = period_bounds(period)
        result = await self._session.execute(
            select(SupplierInvoiceModel).where(
                SupplierInvoiceModel.tenant_id == tenant_id,
                SupplierInvoiceModel.client_id == client_id,
                SupplierInvoiceModel.issue_date >= start,
                SupplierInvoiceModel.issue_date < end,
            )
        )
        return [_to_domain(row) for row in result.scalars()]

    async def save(self, invoice: SupplierInvoice) -> SupplierInvoice:
        existing = await self._session.get(SupplierInvoiceModel, invoice.id)
        if existing:
            _apply_domain_to_model(invoice, existing)
            await self._session.flush()
            return invoice

        # `ProcessImportBatchUseCase` already pre-checks `exists_by_cufe` before
        # constructing new invoices, so this is a defensive re-check against a
        # concurrent import of the same batch rather than the primary dedupe
        # mechanism — the DB's unique constraint on (tenant_id, client_id, cufe)
        # is the actual last line of defense (would raise IntegrityError on a
        # genuine race, which is acceptable to surface as a batch row error).
        if await self.exists_by_cufe(invoice.tenant_id, invoice.client_id, invoice.cufe):
            return invoice

        self._session.add(SupplierInvoiceModel(**_model_kwargs(invoice)))
        await self._session.flush()
        return invoice

    async def delete(self, id: UUID) -> None:
        row = await self._session.get(SupplierInvoiceModel, id)
        if row:
            await self._session.delete(row)
            await self._session.flush()


def _model_kwargs(invoice: SupplierInvoice) -> dict[str, object]:
    return {
        "id": invoice.id,
        "tenant_id": invoice.tenant_id,
        "client_id": invoice.client_id,
        "import_batch_id": invoice.import_batch_id,
        "cufe": invoice.cufe,
        "supplier_nit": invoice.supplier_nit,
        "supplier_name": invoice.supplier_name,
        "issue_date": invoice.issue_date,
        "concept_description": invoice.concept_description,
        "subtotal": invoice.subtotal,
        "vat_amount": invoice.vat_amount,
        "total_amount": invoice.total_amount,
        "status": invoice.status.value,
        "suggested_account_code": invoice.suggested_account_code,
        "suggested_cost_center_id": invoice.suggested_cost_center_id,
        "suggested_confidence": invoice.suggested_confidence,
        "classification_source": invoice.classification_source.value if invoice.classification_source else None,
        "final_account_code": invoice.final_account_code,
        "final_cost_center_id": invoice.final_cost_center_id,
        "classified_by": invoice.classified_by,
        "classified_at": invoice.classified_at,
        "rejection_reason": invoice.rejection_reason,
        "raw_row": invoice.raw_row,
        "created_at": invoice.created_at,
        "updated_at": invoice.updated_at,
    }


def _apply_domain_to_model(invoice: SupplierInvoice, model: SupplierInvoiceModel) -> None:
    for key, value in _model_kwargs(invoice).items():
        setattr(model, key, value)


def _to_domain(model: SupplierInvoiceModel) -> SupplierInvoice:
    return SupplierInvoice(
        id=model.id,
        tenant_id=model.tenant_id,
        client_id=model.client_id,
        import_batch_id=model.import_batch_id,
        cufe=model.cufe,
        supplier_nit=model.supplier_nit,
        supplier_name=model.supplier_name,
        issue_date=model.issue_date,
        concept_description=model.concept_description,
        subtotal=model.subtotal,
        vat_amount=model.vat_amount,
        total_amount=model.total_amount,
        status=InvoiceStatus(model.status),
        suggested_account_code=model.suggested_account_code,
        suggested_cost_center_id=model.suggested_cost_center_id,
        suggested_confidence=model.suggested_confidence,
        classification_source=ClassificationSource(model.classification_source) if model.classification_source else None,
        final_account_code=model.final_account_code,
        final_cost_center_id=model.final_cost_center_id,
        classified_by=model.classified_by,
        classified_at=model.classified_at,
        rejection_reason=model.rejection_reason,
        raw_row=model.raw_row or {},
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
