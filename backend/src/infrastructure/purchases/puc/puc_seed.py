"""PUC (Plan Único de Cuentas, Decreto 2650) subset needed for purchase causación.

This is not the full Colombian chart of accounts — only the expense/cost/tax/
payable accounts a typical purchase invoice can post to. It's the single
source of truth for both the seed data loaded by Alembic migration 0003
(`alembic/versions/0003_puc_seed.py`) and any local re-seeding
(`backend/scripts/seed_puc.py`).
"""
from __future__ import annotations

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
