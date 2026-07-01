from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from src.domain.entities.invoice_import_batch import ImportBatchStatus
from src.domain.entities.supplier_invoice import ClassificationSource, InvoiceStatus


class ImportBatchResponse(BaseModel):
    id: str
    client_id: str
    tenant_id: str
    original_name: str
    status: ImportBatchStatus
    total_rows: int
    new_invoices: int
    duplicate_invoices: int
    error_rows: int
    error_message: str | None
    created_at: str
    updated_at: str


class ImportBatchListResponse(BaseModel):
    items: list[ImportBatchResponse]
    total: int


class SupplierInvoiceResponse(BaseModel):
    id: str
    client_id: str
    import_batch_id: str
    cufe: str
    supplier_nit: str
    supplier_name: str
    issue_date: str
    concept_description: str
    subtotal: Decimal
    vat_amount: Decimal
    total_amount: Decimal
    status: InvoiceStatus
    suggested_account_code: str | None
    suggested_cost_center_id: str | None
    suggested_confidence: float
    classification_source: ClassificationSource | None
    final_account_code: str | None
    final_cost_center_id: str | None
    rejection_reason: str | None


class SupplierInvoiceListResponse(BaseModel):
    items: list[SupplierInvoiceResponse]
    total: int


class ClassifyInvoiceRequest(BaseModel):
    account_code: str
    cost_center_id: str | None = None


class BulkClassifyRequest(BaseModel):
    invoice_ids: list[str]
    account_code: str
    cost_center_id: str | None = None


class RejectInvoiceRequest(BaseModel):
    reason: str


class CausationGenerateRequest(BaseModel):
    client_id: str
    period: str = Field(description="YYYY-MM")
    invoice_ids: list[str] = Field(default_factory=list, description="Empty = all CLASSIFIED invoices for the period")


class CausationEntryLineResponse(BaseModel):
    account_code: str
    debit: Decimal
    credit: Decimal
    description: str
    cost_center_id: str | None


class CausationEntryResponse(BaseModel):
    id: str
    client_id: str
    invoice_id: str
    entry_date: str
    status: str
    external_reference: str | None
    lines: list[CausationEntryLineResponse]


class CausationEntryListResponse(BaseModel):
    items: list[CausationEntryResponse]
    total: int


class CausationGenerateResponse(BaseModel):
    entries: list[CausationEntryResponse]
    reports_triggered: bool
