from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from src.application.use_cases.auth.login import InactiveUserError, InvalidCredentialsError, LoginUseCase
from src.application.use_cases.auth.register import EmailAlreadyExistsError, RegisterUseCase
from src.infrastructure.database.connection import get_session
from src.infrastructure.repositories.tenant_repository import SQLTenantRepository
from src.infrastructure.repositories.user_repository import SQLUserRepository
from src.infrastructure.security.jwt import JWTService
from src.infrastructure.security.password import PasswordService
from src.presentation.middleware.auth import CurrentUser, get_current_user

router = APIRouter()

_password_svc = PasswordService()
_jwt_svc = JWTService()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    use_case = RegisterUseCase(
        user_repo=SQLUserRepository(session),
        tenant_repo=SQLTenantRepository(session),
        password_service=_password_svc,
        jwt_service=_jwt_svc,
    )
    try:
        result = await use_case.execute(body)
        await session.commit()
        return result
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    use_case = LoginUseCase(
        user_repo=SQLUserRepository(session),
        password_service=_password_svc,
        jwt_service=_jwt_svc,
    )
    try:
        return await use_case.execute(body)
    except (InvalidCredentialsError, InactiveUserError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.get("/me", response_model=UserResponse)
async def me(
    current: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    repo = SQLUserRepository(session)
    user = await repo.get_by_id(current.user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role.value,
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        status=user.status.value,
    )
