from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class CreateClientRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    nit: str = Field(min_length=5, max_length=20)
    contact_email: EmailStr
    contact_name: str = Field(default="", max_length=120)
    contact_phone: str = Field(default="", max_length=20)


class UpdateClientRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    contact_email: EmailStr | None = None
    contact_name: str | None = Field(default=None, max_length=120)
    contact_phone: str | None = Field(default=None, max_length=20)
    economic_activity: str | None = Field(default=None, max_length=50)
    ciiu_code: str | None = Field(default=None, max_length=10)


class ClientResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    nit: str
    contact_email: str
    contact_name: str
    contact_phone: str
    economic_activity: str = ""
    ciiu_code: str = ""
    is_active: bool
    created_at: str


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
