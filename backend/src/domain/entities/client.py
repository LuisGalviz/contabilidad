from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class Client:
    tenant_id: UUID
    name: str
    nit: str
    contact_email: str
    id: UUID = field(default_factory=uuid4)
    contact_name: str = ""
    contact_phone: str = ""
    economic_activity: str = ""
    ciiu_code: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)

    def update_contact(self, name: str, email: str, phone: str) -> None:
        self.contact_name = name
        self.contact_email = email
        self.contact_phone = phone
        self.updated_at = datetime.now(timezone.utc)

    def update_economic_activity(self, economic_activity: str, ciiu_code: str = "") -> None:
        self.economic_activity = economic_activity
        self.ciiu_code = ciiu_code
        self.updated_at = datetime.now(timezone.utc)
