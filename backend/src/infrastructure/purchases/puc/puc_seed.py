"""PUC (Plan Único de Cuentas, Decreto 2650) subset needed for purchase causación.

This is not the full Colombian chart of accounts — only the expense/cost/tax/
payable accounts a typical purchase invoice can post to. It's the **starting
point** every new client gets (`build_client_seed_accounts`), not a fixed list:
each company keeps its own chart of accounts and replaces this one by importing
the real one out of its accounting software.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from src.domain.entities.puc_account import PUCAccount

PUC_SEED_ACCOUNTS: list[dict[str, object]] = [
    # Pasivos — el lado crédito de toda causación de compra
    {"code": "22", "name": "Proveedores", "account_class": "pasivo", "parent_code": None},
    {"code": "2205", "name": "Proveedores nacionales", "account_class": "pasivo", "parent_code": "22"},
    {"code": "24", "name": "Impuestos, gravámenes y tasas", "account_class": "pasivo", "parent_code": None},
    {"code": "2408", "name": "Impuesto sobre las ventas por pagar", "account_class": "pasivo", "parent_code": "24"},
    {"code": "240801", "name": "IVA descontable", "account_class": "pasivo", "parent_code": "2408"},
    # Gastos — cuentas típicas para causar compras de servicios/administrativas
    {"code": "5105", "name": "Gastos de personal", "account_class": "gasto", "parent_code": None},
    {"code": "5110", "name": "Honorarios", "account_class": "gasto", "parent_code": None},
    {"code": "5115", "name": "Impuestos", "account_class": "gasto", "parent_code": None},
    {"code": "5120", "name": "Arrendamientos", "account_class": "gasto", "parent_code": None},
    {"code": "5135", "name": "Servicios (públicos, aseo, vigilancia)", "account_class": "gasto", "parent_code": None},
    {"code": "5140", "name": "Gastos legales", "account_class": "gasto", "parent_code": None},
    {"code": "5145", "name": "Mantenimiento y reparaciones", "account_class": "gasto", "parent_code": None},
    {"code": "5150", "name": "Adecuación e instalación", "account_class": "gasto", "parent_code": None},
    {"code": "5155", "name": "Gastos de viaje", "account_class": "gasto", "parent_code": None},
    {"code": "5195", "name": "Diversos (papelería, combustibles, otros)", "account_class": "gasto", "parent_code": None},
    # Costos — para negocios que causan insumos/materia prima (ej. restaurantes)
    {
        "code": "6135",
        "name": "Comercio al por mayor y al por menor (costo de mercancía vendida)",
        "account_class": "costo",
        "parent_code": None,
    },
    {
        "code": "6205",
        "name": "Costo de producción — materia prima consumida",
        "account_class": "costo",
        "parent_code": None,
    },
    # Activos — compras que se activan en vez de gastarse de una vez
    {"code": "1435", "name": "Mercancías no fabricadas por la empresa", "account_class": "activo", "parent_code": None},
    {"code": "1524", "name": "Equipo de oficina", "account_class": "activo", "parent_code": None},
]


def build_client_seed_accounts(tenant_id: UUID, client_id: UUID) -> list[PUCAccount]:
    """Plan de cuentas inicial para un cliente recién creado.

    Sin esto un cliente nuevo nace sin cuentas y la clasificación de facturas
    se queda sin nada que ofrecer. Es un punto de partida usable desde el
    primer día, pensado para ser reemplazado por el plan real de la empresa.
    """
    from src.domain.entities.puc_account import PUCAccount

    return [
        PUCAccount(
            tenant_id=tenant_id,
            client_id=client_id,
            code=str(account["code"]),
            name=str(account["name"]),
            account_class=str(account["account_class"]),
            parent_code=str(account["parent_code"]) if account["parent_code"] is not None else None,
        )
        for account in PUC_SEED_ACCOUNTS
    ]
