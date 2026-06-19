from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog

from src.application.dtos.client import ClientResponse, CreateClientRequest
from src.domain.entities.client import Client
from src.domain.repositories.client_repository import ClientRepository
from src.domain.repositories.tenant_repository import TenantRepository

logger = structlog.get_logger()


class ClientLimitReachedError(Exception):
    pass


class NitAlreadyExistsError(Exception):
    pass


class TenantNotFoundError(Exception):
    pass


@dataclass
class CreateClientUseCase:
    client_repo: ClientRepository
    tenant_repo: TenantRepository

    async def execute(self, tenant_id: UUID, request: CreateClientRequest) -> ClientResponse:
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        current_count = await self.client_repo.count_by_tenant(tenant_id)
        if current_count >= tenant.max_clients:
            raise ClientLimitReachedError(
                f"Plan {tenant.plan} allows up to {tenant.max_clients} clients. "
                "Upgrade your plan to add more."
            )

        if await self.client_repo.nit_exists_in_tenant(request.nit, tenant_id):
            raise NitAlreadyExistsError(f"NIT {request.nit} already registered in this tenant")

        client = Client(
            tenant_id=tenant_id,
            name=request.name,
            nit=request.nit,
            contact_email=request.contact_email,
            contact_name=request.contact_name,
            contact_phone=request.contact_phone,
        )
        saved = await self.client_repo.save(client)

        logger.info("client_created", client_id=str(saved.id), tenant_id=str(tenant_id))

        return ClientResponse(
            id=str(saved.id),
            tenant_id=str(saved.tenant_id),
            name=saved.name,
            nit=saved.nit,
            contact_email=saved.contact_email,
            contact_name=saved.contact_name,
            contact_phone=saved.contact_phone,
            is_active=saved.is_active,
            created_at=saved.created_at.isoformat(),
        )
