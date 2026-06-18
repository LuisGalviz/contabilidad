from __future__ import annotations

from dataclasses import dataclass

import structlog

from src.application.dtos.auth import RegisterRequest, TokenResponse
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User, UserRole
from src.domain.repositories.tenant_repository import TenantRepository
from src.domain.repositories.user_repository import UserRepository
from src.infrastructure.security.jwt import JWTService
from src.infrastructure.security.password import PasswordService

logger = structlog.get_logger()


class EmailAlreadyExistsError(Exception):
    pass


class SlugAlreadyExistsError(Exception):
    pass


@dataclass
class RegisterUseCase:
    user_repo: UserRepository
    tenant_repo: TenantRepository
    password_service: PasswordService
    jwt_service: JWTService

    async def execute(self, request: RegisterRequest) -> TokenResponse:
        if await self.user_repo.email_exists(request.email):
            raise EmailAlreadyExistsError(f"Email {request.email} already registered")

        tenant = Tenant(name=request.tenant_name, owner_email=request.email)

        slug = tenant.slug
        counter = 1
        while await self.tenant_repo.slug_exists(slug):
            slug = f"{tenant.slug}-{counter}"
            counter += 1
        tenant.slug = slug

        saved_tenant = await self.tenant_repo.save(tenant)

        hashed = self.password_service.hash(request.password)
        user = User(
            email=request.email,
            name=request.name,
            hashed_password=hashed,
            role=UserRole.CONTADOR,
            tenant_id=saved_tenant.id,
        )
        user.activate()
        saved_user = await self.user_repo.save(user)

        logger.info("user_registered", user_id=str(saved_user.id), tenant_id=str(saved_tenant.id))

        return self.jwt_service.create_token_pair(
            user_id=str(saved_user.id),
            role=saved_user.role,
            tenant_id=str(saved_tenant.id),
        )
