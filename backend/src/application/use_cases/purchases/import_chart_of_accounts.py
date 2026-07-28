from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import structlog

from src.domain.entities.client_account_setting import AccountRole
from src.domain.entities.puc_account import PUCAccount
from src.domain.repositories.client_account_setting_repository import ClientAccountSettingRepository
from src.domain.repositories.mapping_rule_repository import SupplierMappingRuleRepository
from src.domain.repositories.puc_account_repository import PUCAccountRepository

logger = structlog.get_logger()


@dataclass
class ChartImportResult:
    created: int = 0
    updated: int = 0
    deactivated: int = 0
    warnings: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


@dataclass
class ImportChartOfAccountsUseCase:
    """Reemplaza el plan de cuentas de un cliente por el del archivo importado.

    Nunca borra: las cuentas que dejan de aparecer se marcan inactivas. Hay
    reglas de mapeo aprendidas y facturas ya causadas apuntando a esos códigos,
    y borrarlos dejaría huérfano el histórico contable.
    """

    puc_account_repo: PUCAccountRepository
    mapping_rule_repo: SupplierMappingRuleRepository
    account_setting_repo: ClientAccountSettingRepository

    async def execute(
        self,
        tenant_id: UUID,
        client_id: UUID,
        accounts: list[dict[str, object]],
        messages: list[str] | None = None,
    ) -> ChartImportResult:
        result = ChartImportResult(messages=list(messages or []))

        existing = {a.code: a for a in await self.puc_account_repo.list_active(tenant_id, client_id)}
        incoming_codes = {str(a["code"]) for a in accounts}

        to_save = [
            PUCAccount(
                tenant_id=tenant_id,
                client_id=client_id,
                code=str(account["code"]),
                name=str(account["name"]),
                account_class=str(account["account_class"]),
                requires_cost_center=bool(account["requires_cost_center"]),
                is_active=bool(account["is_active"]),
            )
            for account in accounts
        ]
        await self.puc_account_repo.save_many(to_save)

        result.created = len(incoming_codes - existing.keys())
        result.updated = len(incoming_codes & existing.keys())

        # Las que ya no vienen en el archivo se desactivan, no se borran.
        stale = [account for code, account in existing.items() if code not in incoming_codes]
        if stale:
            for account in stale:
                account.is_active = False
                await self.puc_account_repo.save(account)
            result.deactivated = len(stale)

        await self._warn_about_broken_references(tenant_id, client_id, incoming_codes, stale, result)

        logger.info(
            "chart_of_accounts_imported",
            client_id=str(client_id),
            created=result.created,
            updated=result.updated,
            deactivated=result.deactivated,
        )
        return result

    async def _warn_about_broken_references(
        self,
        tenant_id: UUID,
        client_id: UUID,
        incoming_codes: set[str],
        stale: list[PUCAccount],
        result: ChartImportResult,
    ) -> None:
        """Un plan nuevo puede dejar sin destino a reglas aprendidas o a los
        roles de la causación. Callarlo significa que el contador lo descubre
        cuando la causación falla; se avisa aquí."""
        stale_codes = {account.code for account in stale}
        if not stale_codes:
            return

        rules = await self.mapping_rule_repo.list_by_client(tenant_id, client_id)
        orphan_rules = sorted({rule.account_code for rule in rules if rule.account_code in stale_codes})
        if orphan_rules:
            result.warnings.append(
                f"{len(orphan_rules)} regla(s) de clasificación aprendidas apuntan a cuentas que ya no "
                f"están en el plan: {', '.join(orphan_rules)}. Reclasifica esas facturas para reaprenderlas."
            )

        configured = await self.account_setting_repo.get_codes_by_role(tenant_id, client_id)
        broken_roles = [role for role, code in configured.items() if code in stale_codes]
        if broken_roles:
            result.warnings.append(
                "La configuración contable apunta a cuentas que ya no están en el plan: "
                + ", ".join(f"{_ROLE_LABELS.get(role, role.value)} ({configured[role]})" for role in broken_roles)
                + ". No se podrá causar hasta corregirla."
            )


_ROLE_LABELS: dict[AccountRole, str] = {
    AccountRole.ACCOUNTS_PAYABLE: "Proveedores",
    AccountRole.VAT_DEDUCTIBLE: "IVA descontable",
}
