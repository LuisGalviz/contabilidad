from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


class CausationEntryStatus(str, Enum):
    DRAFT = "draft"
    POSTED = "posted"
    PUSHED_EXTERNAL = "pushed_external"
    FAILED = "failed"


@dataclass
class CausationEntryLine:
    account_code: str
    debit: Decimal
    credit: Decimal
    description: str
    cost_center_id: UUID | None = None


@dataclass
class CausationEntry:
    tenant_id: UUID
    client_id: UUID
    invoice_id: UUID
    entry_date: date
    lines: list[CausationEntryLine]
    id: UUID = field(default_factory=uuid4)
    status: CausationEntryStatus = CausationEntryStatus.DRAFT
    external_reference: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_balanced(self) -> bool:
        total_debit = sum((line.debit for line in self.lines), Decimal("0"))
        total_credit = sum((line.credit for line in self.lines), Decimal("0"))
        return total_debit == total_credit

    def mark_posted(self) -> None:
        self.status = CausationEntryStatus.POSTED
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self) -> None:
        self.status = CausationEntryStatus.FAILED
        self.updated_at = datetime.now(timezone.utc)
