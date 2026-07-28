from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.causation_entry import CausationEntry, CausationEntryStatus
from src.domain.entities.supplier_invoice import SupplierInvoice


class AccountingSystemPort(ABC):
    """Registra la causación de una compra en un sistema contable.

    Recibe el asiento **y la factura** porque no todos los destinos consumen lo
    mismo: el ledger interno y `POST /v1/journals` solo necesitan las líneas
    débito/crédito, mientras que `POST /v1/purchases` de Siigo pide datos de la
    factura (NIT del proveedor, prefijo y número, forma de pago). Pasarla
    explícitamente evita que el adaptador tenga que ir a buscarla a la base.
    """

    @abstractmethod
    async def post_entry(self, entry: CausationEntry, invoice: SupplierInvoice) -> CausationEntry: ...

    @abstractmethod
    async def get_entry_status(self, entry_id: UUID) -> CausationEntryStatus: ...
