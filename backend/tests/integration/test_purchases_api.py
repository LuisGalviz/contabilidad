from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from src.domain.entities.supplier_invoice import SupplierInvoice
from src.infrastructure.repositories.supplier_invoice_repository import SQLSupplierInvoiceRepository

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


def _make_invoice(tenant_id: uuid.UUID, client_id: uuid.UUID, cufe: str) -> SupplierInvoice:
    return SupplierInvoice(
        tenant_id=tenant_id,
        client_id=client_id,
        import_batch_id=uuid.uuid4(),
        cufe=cufe,
        supplier_nit="900123456",
        supplier_name="Distribuidora de Insumos S.A.S.",
        issue_date=date(2026, 1, 15),
        concept_description="Compra de insumos de cocina",
        subtotal=Decimal("100000"),
        vat_amount=Decimal("19000"),
        total_amount=Decimal("119000"),
    )


@pytest.mark.asyncio
class TestSupplierInvoiceDedupe:
    async def test_exists_by_cufe_false_before_save(self, db_session: AsyncSession):
        repo = SQLSupplierInvoiceRepository(db_session)
        tenant_id, client_id = uuid.uuid4(), uuid.uuid4()
        assert not await repo.exists_by_cufe(tenant_id, client_id, "a" * 40)

    async def test_exists_by_cufe_true_after_save(self, db_session: AsyncSession):
        repo = SQLSupplierInvoiceRepository(db_session)
        tenant_id, client_id = uuid.uuid4(), uuid.uuid4()
        cufe = "b" * 40

        await repo.save(_make_invoice(tenant_id, client_id, cufe))
        await db_session.flush()

        assert await repo.exists_by_cufe(tenant_id, client_id, cufe)

    async def test_second_invoice_with_same_cufe_does_not_duplicate(self, db_session: AsyncSession):
        repo = SQLSupplierInvoiceRepository(db_session)
        tenant_id, client_id = uuid.uuid4(), uuid.uuid4()
        cufe = "c" * 40

        await repo.save(_make_invoice(tenant_id, client_id, cufe))
        await db_session.flush()
        # A second insert attempt with the same (tenant, client, cufe) is a no-op
        # at the DB level (on_conflict_do_nothing on the unique constraint) —
        # this is the last line of defense behind the application-level
        # `exists_by_cufe` pre-check in ProcessImportBatchUseCase.
        await repo.save(_make_invoice(tenant_id, client_id, cufe))
        await db_session.flush()

        invoices = await repo.list_by_client(tenant_id, client_id)
        assert len(invoices) == 1

    async def test_different_clients_can_share_a_cufe(self, db_session: AsyncSession):
        repo = SQLSupplierInvoiceRepository(db_session)
        tenant_id = uuid.uuid4()
        cufe = "d" * 40

        await repo.save(_make_invoice(tenant_id, uuid.uuid4(), cufe))
        await repo.save(_make_invoice(tenant_id, uuid.uuid4(), cufe))
        await db_session.flush()

        assert await repo.exists_by_cufe(tenant_id, uuid.uuid4(), cufe) is False


@pytest.mark.asyncio
class TestClientEconomicActivity:
    async def _register_and_create_client(self, client: AsyncClient) -> tuple[str, str]:
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Contador Uno",
                "email": "contador@purchases-test.com",
                "password": "seguro1234",
                "tenant_name": "Estudio Contable Uno",
            },
        )
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.post(
            "/api/v1/clients",
            json={
                "name": "Restaurante El Buen Sabor",
                "nit": "900123456",
                "contact_email": "contacto@buensabor.com",
            },
            headers=headers,
        )
        return created.json()["id"], token

    async def test_update_client_sets_supported_economic_activity(self, client: AsyncClient):
        client_id, token = await self._register_and_create_client(client)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.patch(
            f"/api/v1/clients/{client_id}",
            json={"economic_activity": "restaurante"},
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["economic_activity"] == "restaurante"

    async def test_update_client_rejects_unsupported_economic_activity(self, client: AsyncClient):
        client_id, token = await self._register_and_create_client(client)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.patch(
            f"/api/v1/clients/{client_id}",
            json={"economic_activity": "not-a-real-sector"},
            headers=headers,
        )

        assert response.status_code == 422
