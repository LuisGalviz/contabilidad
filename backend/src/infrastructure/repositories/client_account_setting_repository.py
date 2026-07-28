from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.client_account_setting import AccountRole, ClientAccountSetting
from src.domain.repositories.client_account_setting_repository import ClientAccountSettingRepository
from src.infrastructure.database.models import ClientAccountSettingModel


class SQLClientAccountSettingRepository(ClientAccountSettingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_client(self, tenant_id: UUID, client_id: UUID) -> list[ClientAccountSetting]:
        q = select(ClientAccountSettingModel).where(
            ClientAccountSettingModel.tenant_id == tenant_id,
            ClientAccountSettingModel.client_id == client_id,
        )
        result = await self._session.execute(q.order_by(ClientAccountSettingModel.role))
        return [_to_domain(row) for row in result.scalars()]

    async def get_codes_by_role(self, tenant_id: UUID, client_id: UUID) -> dict[AccountRole, str]:
        return {s.role: s.account_code for s in await self.list_by_client(tenant_id, client_id)}

    async def save_many(self, settings: list[ClientAccountSetting]) -> int:
        if not settings:
            return 0

        stmt = pg_insert(ClientAccountSettingModel).values(
            [
                {
                    "id": setting.id,
                    "tenant_id": setting.tenant_id,
                    "client_id": setting.client_id,
                    "role": setting.role.value,
                    "account_code": setting.account_code,
                }
                for setting in settings
            ]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_client_account_settings_client_role",
            set_={"account_code": stmt.excluded.account_code},
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return len(settings)


def _to_domain(model: ClientAccountSettingModel) -> ClientAccountSetting:
    return ClientAccountSetting(
        id=model.id,
        tenant_id=model.tenant_id,
        client_id=model.client_id,
        role=AccountRole(model.role),
        account_code=model.account_code,
    )
