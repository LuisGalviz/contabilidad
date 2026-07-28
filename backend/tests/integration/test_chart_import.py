from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.use_cases.purchases.import_chart_of_accounts import (
    ImportChartOfAccountsUseCase,
)
from src.domain.entities.client_account_setting import AccountRole, ClientAccountSetting
from src.domain.entities.mapping_rule import SupplierMappingRule
from src.domain.entities.puc_account import PUCAccount
from src.infrastructure.repositories.client_account_setting_repository import (
    SQLClientAccountSettingRepository,
)
from src.infrastructure.repositories.mapping_rule_repository import SQLSupplierMappingRuleRepository
from src.infrastructure.repositories.puc_account_repository import SQLPUCAccountRepository

TENANT = uuid4()
CLIENT = uuid4()
OTHER_CLIENT = uuid4()


def _account(code: str, name: str, client_id=CLIENT) -> PUCAccount:
    return PUCAccount(
        tenant_id=TENANT, client_id=client_id, code=code, name=name, account_class="gasto"
    )


def _incoming(code: str, name: str) -> dict[str, object]:
    return {
        "code": code,
        "name": name,
        "account_class": "gasto",
        "requires_cost_center": False,
        "is_active": True,
    }


def _use_case(session) -> ImportChartOfAccountsUseCase:
    return ImportChartOfAccountsUseCase(
        puc_account_repo=SQLPUCAccountRepository(session),
        mapping_rule_repo=SQLSupplierMappingRuleRepository(session),
        account_setting_repo=SQLClientAccountSettingRepository(session),
    )


class TestPUCAccountIsolation:
    @pytest.mark.asyncio
    async def test_a_client_never_sees_another_clients_accounts(self, db_session):
        repo = SQLPUCAccountRepository(db_session)
        await repo.save_many(
            [_account("5135", "Servicios"), _account("7205", "Costos de obra", client_id=OTHER_CLIENT)]
        )

        mine = await repo.list_active(TENANT, CLIENT)

        assert [a.code for a in mine] == ["5135"]

    @pytest.mark.asyncio
    async def test_same_code_can_mean_different_things_per_client(self, db_session):
        repo = SQLPUCAccountRepository(db_session)
        await repo.save_many(
            [_account("5135", "Aseo y vigilancia"), _account("5135", "Otro uso", client_id=OTHER_CLIENT)]
        )

        assert (await repo.get_by_code(TENANT, CLIENT, "5135")).name == "Aseo y vigilancia"
        assert (await repo.get_by_code(TENANT, OTHER_CLIENT, "5135")).name == "Otro uso"


class TestImportChartOfAccounts:
    @pytest.mark.asyncio
    async def test_creates_updates_and_deactivates(self, db_session):
        repo = SQLPUCAccountRepository(db_session)
        await repo.save_many([_account("5135", "Servicios"), _account("5110", "Honorarios")])

        result = await _use_case(db_session).execute(
            TENANT, CLIENT, [_incoming("5135", "Servicios públicos"), _incoming("5195", "Diversos")]
        )

        assert (result.created, result.updated, result.deactivated) == (1, 1, 1)
        active = {a.code: a.name for a in await repo.list_active(TENANT, CLIENT)}
        assert active == {"5135": "Servicios públicos", "5195": "Diversos"}

    @pytest.mark.asyncio
    async def test_missing_accounts_are_deactivated_not_deleted(self, db_session):
        repo = SQLPUCAccountRepository(db_session)
        await repo.save_many([_account("5110", "Honorarios")])

        await _use_case(db_session).execute(TENANT, CLIENT, [_incoming("5195", "Diversos")])

        # Sigue existiendo: hay facturas causadas apuntando a ese código y
        # borrarlo dejaría huérfano el histórico contable.
        stale = await repo.get_by_code(TENANT, CLIENT, "5110")
        assert stale is not None and stale.is_active is False

    @pytest.mark.asyncio
    async def test_warns_when_a_learned_rule_points_to_a_dropped_account(self, db_session):
        await SQLPUCAccountRepository(db_session).save_many([_account("5110", "Honorarios")])
        await SQLSupplierMappingRuleRepository(db_session).save(
            SupplierMappingRule(tenant_id=TENANT, client_id=CLIENT, supplier_nit="900111", account_code="5110")
        )

        result = await _use_case(db_session).execute(TENANT, CLIENT, [_incoming("5195", "Diversos")])

        assert any("5110" in w and "regla" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_warns_when_the_causation_config_points_to_a_dropped_account(self, db_session):
        await SQLPUCAccountRepository(db_session).save_many([_account("2205", "Proveedores")])
        await SQLClientAccountSettingRepository(db_session).save_many(
            [
                ClientAccountSetting(
                    tenant_id=TENANT, client_id=CLIENT, role=AccountRole.ACCOUNTS_PAYABLE, account_code="2205"
                )
            ]
        )

        result = await _use_case(db_session).execute(TENANT, CLIENT, [_incoming("5195", "Diversos")])

        # Sin este aviso, el contador lo descubre cuando la causación falla.
        assert any("Proveedores" in w and "2205" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_importing_does_not_touch_another_clients_chart(self, db_session):
        repo = SQLPUCAccountRepository(db_session)
        await repo.save_many([_account("5110", "Honorarios", client_id=OTHER_CLIENT)])

        await _use_case(db_session).execute(TENANT, CLIENT, [_incoming("5195", "Diversos")])

        untouched = await repo.list_active(TENANT, OTHER_CLIENT)
        assert [a.code for a in untouched] == ["5110"]
