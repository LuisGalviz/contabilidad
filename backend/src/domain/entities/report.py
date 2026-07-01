from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class ReportType(str, Enum):
    SAZON = "sazon"
    TLG = "tlg"
    MENSUALIZADOS = "mensualizados"
    # System-generated only (see purchases causación feature) — never created
    # via the manual multipart `POST /api/v1/reports` upload flow, see the
    # guard in `presentation/api/v1/reports.py::create_report`.
    PURCHASES_GENERAL = "purchases_general"
    PURCHASES_SECTOR = "purchases_sector"


class ReportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportFile:
    report_id: UUID
    file_type: str
    storage_key: str
    original_name: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Report:
    tenant_id: UUID
    client_id: UUID
    created_by: UUID
    report_type: ReportType
    period: str
    id: UUID = field(default_factory=uuid4)
    status: ReportStatus = field(default=ReportStatus.PENDING)
    error_message: str | None = None
    source_files: list[ReportFile] = field(default_factory=list)
    output_files: list[ReportFile] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def mark_processing(self) -> None:
        self.status = ReportStatus.PROCESSING
        self.updated_at = datetime.now(timezone.utc)

    def mark_completed(self) -> None:
        self.status = ReportStatus.COMPLETED
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        self.status = ReportStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.now(timezone.utc)

    def add_source_file(self, file_type: str, storage_key: str, original_name: str) -> ReportFile:
        rf = ReportFile(
            report_id=self.id,
            file_type=file_type,
            storage_key=storage_key,
            original_name=original_name,
        )
        self.source_files.append(rf)
        return rf

    def add_output_file(self, file_type: str, storage_key: str, original_name: str) -> ReportFile:
        rf = ReportFile(
            report_id=self.id,
            file_type=file_type,
            storage_key=storage_key,
            original_name=original_name,
        )
        self.output_files.append(rf)
        return rf
