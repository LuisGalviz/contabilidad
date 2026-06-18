from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class TenantPlan(str, Enum):
    FREE = "free"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


@dataclass
class Tenant:
    name: str
    owner_email: str
    id: UUID = field(default_factory=uuid4)
    slug: str = ""
    plan: TenantPlan = field(default=TenantPlan.FREE)
    status: TenantStatus = field(default=TenantStatus.ACTIVE)
    max_clients: int = 5
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.slug:
            self.slug = self.name.lower().replace(" ", "-")

    def is_active(self) -> bool:
        return self.status == TenantStatus.ACTIVE

    def upgrade(self, plan: TenantPlan) -> None:
        self.plan = plan
        self.max_clients = {
            TenantPlan.FREE: 5,
            TenantPlan.PROFESSIONAL: 50,
            TenantPlan.ENTERPRISE: 999,
        }[plan]
        self.updated_at = datetime.now(timezone.utc)

    def suspend(self) -> None:
        self.status = TenantStatus.SUSPENDED
        self.updated_at = datetime.now(timezone.utc)
