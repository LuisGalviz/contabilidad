from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4


class AccountRole(str, Enum):
    """Papel que cumple una cuenta en la causación de una compra.

    La causación no puede referirse a códigos fijos: cada empresa usa los
    suyos. En vez de eso nombra el *rol* y el código sale de la configuración
    del cliente. Agregar un rol nuevo (retefuente, reteIVA, reteICA cuando se
    implementen retenciones) es añadir un valor aquí, sin migración.
    """

    ACCOUNTS_PAYABLE = "accounts_payable"
    VAT_DEDUCTIBLE = "vat_deductible"


# Códigos PUC del decreto 2650 con los que arranca un cliente nuevo. Son solo
# el valor inicial: la empresa los cambia por los suyos.
DEFAULT_ROLE_CODES: dict[AccountRole, str] = {
    AccountRole.ACCOUNTS_PAYABLE: "2205",
    AccountRole.VAT_DEDUCTIBLE: "240801",
}


@dataclass
class ClientAccountSetting:
    tenant_id: UUID
    client_id: UUID
    role: AccountRole
    account_code: str
    id: UUID = field(default_factory=uuid4)


def build_default_account_settings(tenant_id: UUID, client_id: UUID) -> list[ClientAccountSetting]:
    return [
        ClientAccountSetting(tenant_id=tenant_id, client_id=client_id, role=role, account_code=code)
        for role, code in DEFAULT_ROLE_CODES.items()
    ]
