from __future__ import annotations

from dataclasses import dataclass

import structlog

from src.application.dtos.auth import LoginRequest, TokenResponse
from src.domain.repositories.user_repository import UserRepository
from src.infrastructure.security.jwt import JWTService
from src.infrastructure.security.password import PasswordService

logger = structlog.get_logger()


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


@dataclass
class LoginUseCase:
    user_repo: UserRepository
    password_service: PasswordService
    jwt_service: JWTService

    async def execute(self, request: LoginRequest) -> TokenResponse:
        user = await self.user_repo.get_by_email(request.email)

        if user is None or not self.password_service.verify(request.password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password")

        if not user.is_active():
            raise InactiveUserError("Account is not active")

        logger.info("user_logged_in", user_id=str(user.id))

        return self.jwt_service.create_token_pair(
            user_id=str(user.id),
            role=user.role,
            tenant_id=str(user.tenant_id) if user.tenant_id else None,
        )
