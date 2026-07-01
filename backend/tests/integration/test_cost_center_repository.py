from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from src.domain.entities.cost_center import CostCenter
from src.infrastructure.repositories.cost_center_repository import SQLCostCenterRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestCostCenterRepository:
    async def test_save_and_list_by_client(self, db_session: AsyncSession):
        repo = SQLCostCenterRepository(db_session)
        tenant_id, client_id = uuid.uuid4(), uuid.uuid4()

        await repo.save(CostCenter(tenant_id=tenant_id, client_id=client_id, code="COC-01", name="Cocina"))
        await repo.save(CostCenter(tenant_id=tenant_id, client_id=client_id, code="SAL-01", name="Salón"))
        await db_session.flush()

        cost_centers = await repo.list_by_client(tenant_id, client_id)
        assert {c.code for c in cost_centers} == {"COC-01", "SAL-01"}

    async def test_deactivated_cost_center_excluded_from_active_list(self, db_session: AsyncSession):
        repo = SQLCostCenterRepository(db_session)
        tenant_id, client_id = uuid.uuid4(), uuid.uuid4()

        cost_center = CostCenter(tenant_id=tenant_id, client_id=client_id, code="COC-01", name="Cocina")
        cost_center.deactivate()
        await repo.save(cost_center)
        await db_session.flush()

        active = await repo.list_by_client(tenant_id, client_id, active_only=True)
        all_of_them = await repo.list_by_client(tenant_id, client_id, active_only=False)
        assert active == []
        assert len(all_of_them) == 1

    async def test_get_by_id_returns_none_when_missing(self, db_session: AsyncSession):
        repo = SQLCostCenterRepository(db_session)
        assert await repo.get_by_id(uuid.uuid4()) is None
