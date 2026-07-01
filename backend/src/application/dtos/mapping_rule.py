from __future__ import annotations

from pydantic import BaseModel


class MappingRuleResponse(BaseModel):
    id: str
    client_id: str
    supplier_nit: str
    concept_keywords: list[str]
    account_code: str
    cost_center_id: str | None
    confidence: float
    times_confirmed: int
    times_corrected: int
    is_active: bool


class MappingRuleListResponse(BaseModel):
    items: list[MappingRuleResponse]


class ClassificationHistoryResponse(BaseModel):
    id: str
    invoice_id: str
    action: str
    account_code_before: str | None
    account_code_after: str | None
    rule_id: str | None
    user_id: str | None
    created_at: str


class ClassificationHistoryListResponse(BaseModel):
    items: list[ClassificationHistoryResponse]


class PUCAccountResponse(BaseModel):
    code: str
    name: str
    account_class: str
    requires_cost_center: bool


class PUCAccountListResponse(BaseModel):
    items: list[PUCAccountResponse]
