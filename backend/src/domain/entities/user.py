from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class UserRole(str, Enum):
    ADMIN = "admin"
    CONTADOR = "contador"
    EMPRESA = "empresa"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


@dataclass
class User:
    email: str
    name: str
    hashed_password: str
    role: UserRole
    id: UUID = field(default_factory=uuid4)
    tenant_id: UUID | None = None
    status: UserStatus = field(default=UserStatus.PENDING)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def activate(self) -> None:
        self.status = UserStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)

    def deactivate(self) -> None:
        self.status = UserStatus.INACTIVE
        self.updated_at = datetime.now(timezone.utc)

    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    def belongs_to_tenant(self, tenant_id: UUID) -> bool:
        return self.tenant_id == tenant_id

    def can_manage_tenant(self, tenant_id: UUID) -> bool:
        if self.role == UserRole.ADMIN:
            return True
        return self.role == UserRole.CONTADOR and self.tenant_id == tenant_id
