from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

MAX_CONFIDENCE = 0.98
MIN_CONFIDENCE = 0.1


@dataclass
class SupplierMappingRule:
    tenant_id: UUID
    client_id: UUID
    supplier_nit: str
    account_code: str
    id: UUID = field(default_factory=uuid4)
    concept_keywords: list[str] = field(default_factory=list)
    cost_center_id: UUID | None = None
    confidence: float = 0.5
    times_confirmed: int = 0
    times_corrected: int = 0
    created_by: UUID | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def record_confirmation(self) -> None:
        self.times_confirmed += 1
        self.confidence = min(MAX_CONFIDENCE, self.confidence + 0.15)
        self.updated_at = datetime.now(timezone.utc)

    def record_correction(self, new_account_code: str, new_cost_center_id: UUID | None = None) -> None:
        self.times_corrected += 1
        self.account_code = new_account_code
        self.cost_center_id = new_cost_center_id
        self.confidence = max(MIN_CONFIDENCE, self.confidence - 0.25)
        self.updated_at = datetime.now(timezone.utc)
