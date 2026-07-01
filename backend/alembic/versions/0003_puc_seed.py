"""seed data: PUC accounts subset for purchase causación

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-01

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from src.infrastructure.purchases.puc.puc_seed import PUC_SEED_ACCOUNTS

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

puc_accounts_table = sa.table(
    "puc_accounts",
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("account_class", sa.String),
    sa.column("parent_code", sa.String),
    sa.column("requires_cost_center", sa.Boolean),
    sa.column("is_active", sa.Boolean),
)


def upgrade() -> None:
    rows = [
        {
            "code": account["code"],
            "name": account["name"],
            "account_class": account["account_class"],
            "parent_code": account["parent_code"],
            "requires_cost_center": False,
            "is_active": True,
        }
        for account in PUC_SEED_ACCOUNTS
    ]
    op.bulk_insert(puc_accounts_table, rows)


def downgrade() -> None:
    codes = tuple(account["code"] for account in PUC_SEED_ACCOUNTS)
    op.execute(puc_accounts_table.delete().where(puc_accounts_table.c.code.in_(codes)))
