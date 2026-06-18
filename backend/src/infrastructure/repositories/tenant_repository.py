from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.tenant import Tenant, TenantPlan, TenantStatus
from src.domain.repositories.tenant_repository import TenantRepository
from src.infrastructure.database.models import TenantModel


class SQLTenantRepository(TenantRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Tenant | None:
        result = await self._session.get(TenantModel, id)
        return _to_domain(result) if result else None

    async def get_by_slug(self, slug: str) -> Tenant | None:
        result = await self._session.execute(select(TenantModel).where(TenantModel.slug == slug))
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def slug_exists(self, slug: str) -> bool:
        result = await self._session.execute(select(TenantModel.id).where(TenantModel.slug == slug))
        return result.scalar_one_or_none() is not None

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[Tenant]:
        result = await self._session.execute(select(TenantModel).limit(limit).offset(offset))
        return [_to_domain(row) for row in result.scalars()]

    async def save(self, tenant: Tenant) -> Tenant:
        existing = await self._session.get(TenantModel, tenant.id)
        if existing:
            existing.name = tenant.name
            existing.slug = tenant.slug
            existing.plan = tenant.plan.value
            existing.status = tenant.status.value
            existing.max_clients = tenant.max_clients
            await self._session.flush()
            return _to_domain(existing)

        model = TenantModel(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            owner_email=tenant.owner_email,
            plan=tenant.plan.value,
            status=tenant.status.value,
            max_clients=tenant.max_clients,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_domain(model)

    async def delete(self, id: UUID) -> None:
        row = await self._session.get(TenantModel, id)
        if row:
            await self._session.delete(row)
            await self._session.flush()


def _to_domain(model: TenantModel) -> Tenant:
    t = Tenant(
        id=model.id,
        name=model.name,
        owner_email=model.owner_email,
        plan=TenantPlan(model.plan),
        status=TenantStatus(model.status),
        max_clients=model.max_clients,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
    t.slug = model.slug
    return t
