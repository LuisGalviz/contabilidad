from __future__ import annotations

from pydantic import BaseModel, Field

from src.domain.entities.report import ReportStatus, ReportType


class CreateReportRequest(BaseModel):
    client_id: str
    report_type: ReportType
    period: str = Field(default="", description="Auto-detected from files if empty")


class ReportFileResponse(BaseModel):
    id: str
    file_type: str
    original_name: str
    storage_key: str


class ReportResponse(BaseModel):
    id: str
    client_id: str
    tenant_id: str
    report_type: ReportType
    period: str
    status: ReportStatus
    error_message: str | None
    source_files: list[ReportFileResponse]
    output_files: list[ReportFileResponse]
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class ReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int
