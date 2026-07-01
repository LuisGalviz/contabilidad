from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog

from src.domain.entities.invoice_import_batch import InvoiceImportBatch
from src.domain.repositories.client_repository import ClientRepository
from src.domain.repositories.import_batch_repository import InvoiceImportBatchRepository

logger = structlog.get_logger()


class ClientNotFoundError(Exception):
    pass


class ClientNotInTenantError(Exception):
    pass


@dataclass
class CreateImportBatchUseCase:
    batch_repo: InvoiceImportBatchRepository
    client_repo: ClientRepository

    async def execute(
        self,
        tenant_id: UUID,
        uploaded_by: UUID,
        client_id: UUID,
        source_file_key: str,
        original_name: str,
    ) -> InvoiceImportBatch:
        client = await self.client_repo.get_by_id(client_id)
        if client is None:
            raise ClientNotFoundError(f"Client {client_id} not found")
        if client.tenant_id != tenant_id:
            raise ClientNotInTenantError("Client does not belong to this tenant")

        batch = InvoiceImportBatch(
            tenant_id=tenant_id,
            client_id=client_id,
            uploaded_by=uploaded_by,
            source_file_key=source_file_key,
            original_name=original_name,
        )
        saved = await self.batch_repo.save(batch)

        logger.info("import_batch_created", batch_id=str(saved.id), client_id=str(client_id))
        return saved
