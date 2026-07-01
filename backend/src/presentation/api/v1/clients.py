from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.client import ClientListResponse, ClientResponse, CreateClientRequest, UpdateClientRequest
from src.application.use_cases.clients.create_client import (
    ClientLimitReachedError,
    CreateClientUseCase,
    NitAlreadyExistsError,
    TenantNotFoundError,
)
from src.application.use_cases.clients.update_client import (
    ClientNotFoundError,
    InvalidEconomicActivityError,
    UpdateClientUseCase,
)
from src.infrastructure.database.connection import get_session
from src.infrastructure.repositories.client_repository import SQLClientRepository
from src.infrastructure.repositories.tenant_repository import SQLTenantRepository
from src.presentation.middleware.auth import CurrentUser, require_contador

router = APIRouter()


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    body: CreateClientRequest,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> ClientResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    use_case = CreateClientUseCase(
        client_repo=SQLClientRepository(session),
        tenant_repo=SQLTenantRepository(session),
    )
    try:
        result = await use_case.execute(current.tenant_id, body)
        await session.commit()
        return result
    except TenantNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ClientLimitReachedError as exc:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)) from exc
    except NitAlreadyExistsError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=ClientListResponse)
async def list_clients(
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> ClientListResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    repo = SQLClientRepository(session)
    clients = await repo.list_by_tenant(current.tenant_id)
    items = [
        ClientResponse(
            id=str(c.id),
            tenant_id=str(c.tenant_id),
            name=c.name,
            nit=c.nit,
            contact_email=c.contact_email,
            contact_name=c.contact_name,
            contact_phone=c.contact_phone,
            economic_activity=c.economic_activity,
            ciiu_code=c.ciiu_code,
            is_active=c.is_active,
            created_at=c.created_at.isoformat(),
        )
        for c in clients
    ]
    return ClientListResponse(items=items, total=len(items))


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str,
    body: UpdateClientRequest,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> ClientResponse:
    from uuid import UUID

    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    use_case = UpdateClientUseCase(client_repo=SQLClientRepository(session))
    try:
        result = await use_case.execute(current.tenant_id, UUID(client_id), body)
        await session.commit()
        return result
    except ClientNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidEconomicActivityError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_client(
    client_id: str,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> None:
    from uuid import UUID

    repo = SQLClientRepository(session)
    client = await repo.get_by_id(UUID(client_id))
    if not client or client.tenant_id != current.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Client not found")
    client.deactivate()
    await repo.save(client)
    await session.commit()
