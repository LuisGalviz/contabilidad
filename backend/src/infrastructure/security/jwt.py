from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from jose import JWTError, jwt

from src.application.dtos.auth import TokenResponse
from src.config import get_settings
from src.domain.entities.user import UserRole


class TokenExpiredError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


@dataclass
class TokenPayload:
    sub: str
    role: str
    tenant_id: str | None
    exp: datetime
    type: str


class JWTService:
    def __init__(self) -> None:
        s = get_settings()
        self._secret = s.jwt_secret_key
        self._algorithm = s.jwt_algorithm
        self._access_minutes = s.jwt_access_token_expire_minutes
        self._refresh_days = s.jwt_refresh_token_expire_days

    def create_token_pair(
        self,
        user_id: str,
        role: UserRole,
        tenant_id: str | None,
    ) -> TokenResponse:
        access = self._encode(user_id, role, tenant_id, "access", self._access_minutes * 60)
        refresh = self._encode(user_id, role, tenant_id, "refresh", self._refresh_days * 86400)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=self._access_minutes * 60,
        )

    def decode(self, token: str) -> TokenPayload:
        try:
            data = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except JWTError as exc:
            raise InvalidTokenError(str(exc)) from exc

        exp = datetime.fromtimestamp(data["exp"], tz=timezone.utc)
        if exp < datetime.now(timezone.utc):
            raise TokenExpiredError("Token has expired")

        return TokenPayload(
            sub=data["sub"],
            role=data["role"],
            tenant_id=data.get("tenant_id"),
            exp=exp,
            type=data.get("type", "access"),
        )

    def _encode(
        self,
        user_id: str,
        role: UserRole,
        tenant_id: str | None,
        token_type: str,
        expires_in_seconds: int,
    ) -> str:
        exp = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
        payload = {
            "sub": user_id,
            "role": role.value,
            "tenant_id": tenant_id,
            "type": token_type,
            "exp": exp,
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)
