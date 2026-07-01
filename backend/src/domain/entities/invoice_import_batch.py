from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class ImportBatchStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class InvoiceImportBatch:
    tenant_id: UUID
    client_id: UUID
    uploaded_by: UUID
    source_file_key: str
    original_name: str
    id: UUID = field(default_factory=uuid4)
    status: ImportBatchStatus = ImportBatchStatus.PENDING
    total_rows: int = 0
    new_invoices: int = 0
    duplicate_invoices: int = 0
    error_rows: int = 0
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def mark_processing(self) -> None:
        self.status = ImportBatchStatus.PROCESSING
        self.updated_at = datetime.now(timezone.utc)

    def mark_completed(self, total_rows: int, new_invoices: int, duplicate_invoices: int, error_rows: int) -> None:
        self.status = ImportBatchStatus.COMPLETED
        self.total_rows = total_rows
        self.new_invoices = new_invoices
        self.duplicate_invoices = duplicate_invoices
        self.error_rows = error_rows
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        self.status = ImportBatchStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.now(timezone.utc)
