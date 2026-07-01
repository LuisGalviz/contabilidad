from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PUCAccount:
    code: str
    name: str
    account_class: str
    parent_code: str | None = None
    requires_cost_center: bool = False
    is_active: bool = True
