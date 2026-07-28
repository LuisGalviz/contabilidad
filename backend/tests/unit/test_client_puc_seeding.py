from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from src.application.dtos.client import CreateClientRequest
from src.application.use_cases.clients.create_client import CreateClientUseCase
from src.domain.entities.client import Client
from src.domain.entities.client_account_setting import AccountRole, ClientAccountSetting
from src.domain.entities.puc_account import PUCAccount
from src.domain.entities.tenant import Tenant
from src.infrastructure.purchases.puc.puc_seed import PUC_SEED_ACCOUNTS, build_client_seed_accounts


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


class TestBuildClientSeedAccounts:
    def test_every_account_is_scoped_to_the_client(self):
        tenant_id, client_id = uuid4(), uuid4()

        accounts = build_client_seed_accounts(tenant_id, client_id)

        assert len(accounts) == len(PUC_SEED_ACCOUNTS)
        assert all(a.tenant_id == tenant_id and a.client_id == client_id for a in accounts)

    def test_two_clients_get_independent_accounts(self):
        tenant_id = uuid4()
        first, second = uuid4(), uuid4()

        a = build_client_seed_accounts(tenant_id, first)
        b = build_client_seed_accounts(tenant_id, second)

        # Mismos códigos, filas distintas: es lo que permite que cada empresa
        # edite su plan sin tocar el de las demás.
        assert {x.code for x in a} == {x.code for x in b}
        assert {x.id for x in a}.isdisjoint({x.id for x in b})


class TestCreateClientSeedsPUC:
    @pytest.mark.asyncio
    async def test_new_client_gets_its_own_chart_of_accounts(self):
        tenant_id = uuid4()
        tenant = Tenant(id=tenant_id, name="Firma", slug="firma", owner_email="a@x.co")
        client_repo, puc_repo = FakeClientRepo(), FakePUCRepo()
        setting_repo = FakeAccountSettingRepo()
        use_case = CreateClientUseCase(
            client_repo=client_repo,  # type: ignore[arg-type]
            tenant_repo=FakeTenantRepo(tenant),  # type: ignore[arg-type]
            puc_account_repo=puc_repo,  # type: ignore[arg-type]
            account_setting_repo=setting_repo,  # type: ignore[arg-type]
        )

        result = await use_case.execute(
            tenant_id,
            CreateClientRequest(name="Rest Uno", nit="900111", contact_email="a@x.co", contact_name="A"),
        )

        # Sin cuentas no se puede clasificar ninguna factura, así que un cliente
        # recién creado no puede quedar con el plan vacío.
        assert len(puc_repo.saved) == len(PUC_SEED_ACCOUNTS)
        assert {a.client_id for a in puc_repo.saved} == {UUID(result.id)}
        assert {a.tenant_id for a in puc_repo.saved} == {tenant_id}

    @pytest.mark.asyncio
    async def test_new_client_gets_its_causation_roles_configured(self):
        tenant_id = uuid4()
        tenant = Tenant(id=tenant_id, name="Firma", slug="firma", owner_email="a@x.co")
        setting_repo = FakeAccountSettingRepo()
        use_case = CreateClientUseCase(
            client_repo=FakeClientRepo(),  # type: ignore[arg-type]
            tenant_repo=FakeTenantRepo(tenant),  # type: ignore[arg-type]
            puc_account_repo=FakePUCRepo(),  # type: ignore[arg-type]
            account_setting_repo=setting_repo,  # type: ignore[arg-type]
        )

        await use_case.execute(
            tenant_id,
            CreateClientRequest(name="Rest Uno", nit="900111", contact_email="a@x.co", contact_name="A"),
        )

        # La causación exige configuración explícita: sin estos roles un cliente
        # nuevo no podría causar ni una factura.
        by_role = {s.role: s.account_code for s in setting_repo.saved}
        assert by_role == {AccountRole.ACCOUNTS_PAYABLE: "2205", AccountRole.VAT_DEDUCTIBLE: "240801"}
