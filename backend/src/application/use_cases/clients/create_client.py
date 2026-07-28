from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog

from src.application.dtos.client import ClientResponse, CreateClientRequest
from src.domain.entities.client import Client
from src.domain.repositories.client_account_setting_repository import ClientAccountSettingRepository
from src.domain.repositories.client_repository import ClientRepository
from src.domain.repositories.puc_account_repository import PUCAccountRepository
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
    puc_account_repo: PUCAccountRepository
    account_setting_repo: ClientAccountSettingRepository

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

        # El cliente nace **sin plan de cuentas**. Sembrar el subconjunto PUC del
        # decreto parecía útil, pero los códigos reales de una empresa en Siigo
        # son auxiliares de 8 dígitos (22050501, 24081001) y ninguno de los del
        # decreto existe allá como cuenta de movimiento. Sembrarlos mostraba
        # cuentas que parecían usables y que Siigo habría rechazado, y dejaba
        # huérfanas las clasificaciones hechas contra ellas al importar el plan
        # real. El plan se carga desde "Plan de cuentas" antes de clasificar.

        logger.info("client_created", client_id=str(saved.id), tenant_id=str(tenant_id))

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
