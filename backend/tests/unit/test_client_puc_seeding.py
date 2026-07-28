from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from src.application.dtos.client import CreateClientRequest
from src.application.use_cases.clients.create_client import CreateClientUseCase
from src.domain.entities.client import Client
from src.domain.entities.client_account_setting import ClientAccountSetting
from src.domain.entities.puc_account import PUCAccount
from src.domain.entities.tenant import Tenant


class FakeClientRepo:
    def __init__(self) -> None:
        self.saved: list[Client] = []

    async def count_by_tenant(self, tenant_id: UUID) -> int:
        return 0

    async def nit_exists_in_tenant(self, nit: str, tenant_id: UUID) -> bool:
        return False

    async def save(self, client: Client) -> Client:
        self.saved.append(client)
        return client


class FakeTenantRepo:
    def __init__(self, tenant: Tenant | None) -> None:
        self._tenant = tenant

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        return self._tenant


class FakePUCRepo:
    def __init__(self) -> None:
        self.saved: list[PUCAccount] = []

    async def save_many(self, accounts: list[PUCAccount]) -> int:
        self.saved.extend(accounts)
        return len(accounts)


class FakeAccountSettingRepo:
    def __init__(self) -> None:
        self.saved: list[ClientAccountSetting] = []

    async def save_many(self, settings: list[ClientAccountSetting]) -> int:
        self.saved.extend(settings)
        return len(settings)


class TestNewClientStartsWithoutAChartOfAccounts:
    """Sembrar el subconjunto PUC del decreto parecia util, pero los codigos
    reales de una empresa en Siigo son auxiliares de 8 digitos y ninguno de los
    del decreto existe alla como cuenta de movimiento: mostraba cuentas que
    Siigo habria rechazado. El plan se importa desde Siigo."""

    @pytest.mark.asyncio
    async def test_no_accounts_are_created(self):
        tenant_id = uuid4()
        puc_repo, setting_repo = FakePUCRepo(), FakeAccountSettingRepo()
        use_case = CreateClientUseCase(
            client_repo=FakeClientRepo(),  # type: ignore[arg-type]
            tenant_repo=FakeTenantRepo(  # type: ignore[arg-type]
                Tenant(id=tenant_id, name="Firma", slug="firma", owner_email="a@x.co")
            ),
            puc_account_repo=puc_repo,  # type: ignore[arg-type]
            account_setting_repo=setting_repo,  # type: ignore[arg-type]
        )

        result = await use_case.execute(
            tenant_id,
            CreateClientRequest(name="Rest Uno", nit="900111", contact_email="a@x.co", contact_name="A"),
        )

        assert UUID(result.id)
        assert puc_repo.saved == []
        assert setting_repo.saved == []
