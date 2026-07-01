from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


class InvoiceStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    CLASSIFIED = "classified"
    CAUSED = "caused"
    REJECTED = "rejected"
    ERROR = "error"


class ClassificationSource(str, Enum):
    AUTO_HIGH_CONFIDENCE = "auto_high_confidence"
    AUTO_LOW_CONFIDENCE = "auto_low_confidence"
    MANUAL = "manual"


@dataclass
class SupplierInvoice:
    tenant_id: UUID
    client_id: UUID
    import_batch_id: UUID
    cufe: str
    supplier_nit: str
    supplier_name: str
    issue_date: date
    concept_description: str
    subtotal: Decimal
    vat_amount: Decimal
    total_amount: Decimal
    id: UUID = field(default_factory=uuid4)
    status: InvoiceStatus = InvoiceStatus.PENDING_REVIEW
    suggested_account_code: str | None = None
    suggested_cost_center_id: UUID | None = None
    suggested_confidence: float = 0.0
    classification_source: ClassificationSource | None = None
    final_account_code: str | None = None
    final_cost_center_id: UUID | None = None
    classified_by: UUID | None = None
    classified_at: datetime | None = None
    rejection_reason: str | None = None
    raw_row: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def apply_suggestion(
        self,
        account_code: str,
        cost_center_id: UUID | None,
        confidence: float,
        source: ClassificationSource,
    ) -> None:
        self.suggested_account_code = account_code
        self.suggested_cost_center_id = cost_center_id
        self.suggested_confidence = confidence
        self.classification_source = source
        self.updated_at = datetime.now(timezone.utc)

    def confirm_classification(
        self,
        account_code: str,
        cost_center_id: UUID | None,
        user_id: UUID | None,
    ) -> None:
        """`user_id=None` marks a system auto-confirmation (high-confidence
        rule applied without a human looking at it yet) rather than a manual
        confirm/correct action."""
        self.final_account_code = account_code
        self.final_cost_center_id = cost_center_id
        self.classified_by = user_id
        self.classified_at = datetime.now(timezone.utc)
        self.status = InvoiceStatus.CLASSIFIED
        self.updated_at = datetime.now(timezone.utc)

    def reject(self, reason: str) -> None:
        self.status = InvoiceStatus.REJECTED
        self.rejection_reason = reason
        self.updated_at = datetime.now(timezone.utc)

    def mark_caused(self) -> None:
        self.status = InvoiceStatus.CAUSED
        self.updated_at = datetime.now(timezone.utc)

    def was_suggestion_accepted(self, account_code: str) -> bool:
        return self.suggested_account_code == account_code
