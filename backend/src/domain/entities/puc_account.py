from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class PUCAccount:
    """Una cuenta del plan de cuentas de **un cliente**, no del sistema.

    Cada empresa lleva su propio plan de cuentas (y en Siigo cada compañía
    tiene el suyo), así que el código solo es único dentro de un `client_id`.
    """

    tenant_id: UUID
    client_id: UUID
    code: str
    name: str
    account_class: str
    parent_code: str | None = None
    requires_cost_center: bool = False
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)
