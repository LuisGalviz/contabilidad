from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class ClassificationAction(str, Enum):
    AUTO_SUGGESTED = "auto_suggested"
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"
    REJECTED = "rejected"


@dataclass
class ClassificationHistoryEntry:
    invoice_id: UUID
    tenant_id: UUID
    action: ClassificationAction
    id: UUID = field(default_factory=uuid4)
    account_code_before: str | None = None
    account_code_after: str | None = None
    rule_id: UUID | None = None
    user_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
