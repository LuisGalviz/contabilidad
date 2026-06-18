from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_session
from src.infrastructure.repositories.tenant_repository import SQLTenantRepository
from src.presentation.middleware.auth import CurrentUser, require_admin, require_contador

router = APIRouter()


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    status: str
    max_clients: int
    owner_email: str
    created_at: str


@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> TenantResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No tenant associated")

    repo = SQLTenantRepository(session)
    tenant = await repo.get_by_id(current.tenant_id)
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    return TenantResponse(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan.value,
        status=tenant.status.value,
        max_clients=tenant.max_clients,
        owner_email=tenant.owner_email,
        created_at=tenant.created_at.isoformat(),
    )


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    limit: int = 50,
    offset: int = 0,
    current: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[TenantResponse]:
    repo = SQLTenantRepository(session)
    tenants = await repo.list_all(limit=limit, offset=offset)
    return [
        TenantResponse(
            id=str(t.id),
            name=t.name,
            slug=t.slug,
            plan=t.plan.value,
            status=t.status.value,
            max_clients=t.max_clients,
            owner_email=t.owner_email,
            created_at=t.created_at.isoformat(),
        )
        for t in tenants
    ]
