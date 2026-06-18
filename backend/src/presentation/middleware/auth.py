from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.domain.entities.user import UserRole
from src.infrastructure.security.jwt import InvalidTokenError, JWTService, TokenExpiredError, TokenPayload

_bearer = HTTPBearer()
_jwt = JWTService()


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    role: UserRole
    tenant_id: UUID | None


def _decode(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> TokenPayload:
    try:
        payload = _jwt.decode(credentials.credentials)
    except TokenExpiredError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.type != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    return payload


def get_current_user(payload: TokenPayload = Depends(_decode)) -> CurrentUser:
    return CurrentUser(
        user_id=UUID(payload.sub),
        role=UserRole(payload.role),
        tenant_id=UUID(payload.tenant_id) if payload.tenant_id else None,
    )


def require_role(*roles: UserRole):  # type: ignore[no-untyped-def]
    def _check(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current

    return _check


require_admin = require_role(UserRole.ADMIN)
require_contador = require_role(UserRole.ADMIN, UserRole.CONTADOR)
require_any = require_role(UserRole.ADMIN, UserRole.CONTADOR, UserRole.EMPRESA)
