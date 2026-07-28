from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.client_account_setting import AccountRole, ClientAccountSetting


class ClientAccountSettingRepository(ABC):
    @abstractmethod
    async def list_by_client(self, tenant_id: UUID, client_id: UUID) -> list[ClientAccountSetting]: ...

    @abstractmethod
    async def get_codes_by_role(self, tenant_id: UUID, client_id: UUID) -> dict[AccountRole, str]:
        """Configuración lista para consumir en la causación."""

    @abstractmethod
    async def save_many(self, settings: list[ClientAccountSetting]) -> int: ...
