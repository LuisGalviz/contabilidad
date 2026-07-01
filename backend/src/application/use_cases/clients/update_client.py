from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog

from src.application.dtos.client import ClientResponse, UpdateClientRequest
from src.domain.repositories.client_repository import ClientRepository
from src.infrastructure.reporting.sector_templates.registry import sector_keys

logger = structlog.get_logger()


class ClientNotFoundError(Exception):
    pass


class InvalidEconomicActivityError(Exception):
    pass


@dataclass
class UpdateClientUseCase:
    client_repo: ClientRepository

    async def execute(self, tenant_id: UUID, client_id: UUID, request: UpdateClientRequest) -> ClientResponse:
        client = await self.client_repo.get_by_id(client_id)
        if client is None or client.tenant_id != tenant_id:
            raise ClientNotFoundError(f"Client {client_id} not found")

        if request.name is not None:
            client.name = request.name
        if request.contact_email is not None or request.contact_name is not None or request.contact_phone is not None:
            client.update_contact(
                request.contact_name if request.contact_name is not None else client.contact_name,
                request.contact_email if request.contact_email is not None else client.contact_email,
                request.contact_phone if request.contact_phone is not None else client.contact_phone,
            )
        if request.economic_activity is not None:
            if request.economic_activity and request.economic_activity not in sector_keys():
                raise InvalidEconomicActivityError(f"Unsupported economic_activity: {request.economic_activity}")
            client.update_economic_activity(request.economic_activity, request.ciiu_code or "")

        saved = await self.client_repo.save(client)
        logger.info("client_updated", client_id=str(saved.id))

        return ClientResponse(
            id=str(saved.id),
            tenant_id=str(saved.tenant_id),
            name=saved.name,
            nit=saved.nit,
            contact_email=saved.contact_email,
            contact_name=saved.contact_name,
            contact_phone=saved.contact_phone,
            economic_activity=saved.economic_activity,
            ciiu_code=saved.ciiu_code,
            is_active=saved.is_active,
            created_at=saved.created_at.isoformat(),
        )
