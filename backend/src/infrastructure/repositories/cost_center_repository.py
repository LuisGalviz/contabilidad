from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.cost_center import CostCenter
from src.domain.repositories.cost_center_repository import CostCenterRepository
from src.infrastructure.database.models import CostCenterModel


class SQLCostCenterRepository(CostCenterRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> CostCenter | None:
        row = await self._session.get(CostCenterModel, id)
        return _to_domain(row) if row else None

    async def list_by_client(self, tenant_id: UUID, client_id: UUID, active_only: bool = True) -> list[CostCenter]:
        q = select(CostCenterModel).where(CostCenterModel.tenant_id == tenant_id, CostCenterModel.client_id == client_id)
        if active_only:
            q = q.where(CostCenterModel.is_active.is_(True))
        result = await self._session.execute(q.order_by(CostCenterModel.code))
        return [_to_domain(row) for row in result.scalars()]

    async def save(self, cost_center: CostCenter) -> CostCenter:
        existing = await self._session.get(CostCenterModel, cost_center.id)
        if existing:
            existing.code = cost_center.code
            existing.name = cost_center.name
            existing.is_active = cost_center.is_active
            existing.updated_at = cost_center.updated_at
            await self._session.flush()
            return cost_center

        model = CostCenterModel(
            id=cost_center.id,
            tenant_id=cost_center.tenant_id,
            client_id=cost_center.client_id,
            code=cost_center.code,
            name=cost_center.name,
            is_active=cost_center.is_active,
            created_at=cost_center.created_at,
            updated_at=cost_center.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return cost_center

    async def delete(self, id: UUID) -> None:
        row = await self._session.get(CostCenterModel, id)
        if row:
            await self._session.delete(row)
            await self._session.flush()


def _to_domain(model: CostCenterModel) -> CostCenter:
    return CostCenter(
        id=model.id,
        tenant_id=model.tenant_id,
        client_id=model.client_id,
        code=model.code,
        name=model.name,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
