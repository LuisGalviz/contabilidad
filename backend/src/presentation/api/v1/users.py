from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.auth import UserResponse
from src.domain.entities.user import UserRole
from src.infrastructure.database.connection import get_session
from src.infrastructure.repositories.user_repository import SQLUserRepository
from src.infrastructure.security.password import PasswordService
from src.presentation.middleware.auth import CurrentUser, require_contador

router = APIRouter()

_password_svc = PasswordService()


class InviteUserRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: UserRole = UserRole.EMPRESA


@router.get("", response_model=list[UserResponse])
async def list_users(
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> list[UserResponse]:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    repo = SQLUserRepository(session)
    users = await repo.list_by_tenant(current.tenant_id)
    return [
        UserResponse(
            id=str(u.id),
            email=u.email,
            name=u.name,
            role=u.role.value,
            tenant_id=str(u.tenant_id) if u.tenant_id else None,
            status=u.status.value,
        )
        for u in users
    ]


@router.post("/invite", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    body: InviteUserRequest,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    repo = SQLUserRepository(session)

    if await repo.email_exists(body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")

    from src.domain.entities.user import User

    user = User(
        email=body.email,
        name=body.name,
        hashed_password=_password_svc.hash(body.password),
        role=body.role,
        tenant_id=current.tenant_id,
    )
    user.activate()
    saved = await repo.save(user)
    await session.commit()

    return UserResponse(
        id=str(saved.id),
        email=saved.email,
        name=saved.name,
        role=saved.role.value,
        tenant_id=str(saved.tenant_id) if saved.tenant_id else None,
        status=saved.status.value,
    )
