from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import structlog

from src.application.dtos.report import CreateReportRequest, ReportResponse
from src.domain.entities.report import Report
from src.domain.repositories.client_repository import ClientRepository
from src.domain.repositories.report_repository import ReportRepository

logger = structlog.get_logger()


class ClientNotFoundError(Exception):
    pass


class ClientNotInTenantError(Exception):
    pass


@dataclass
class CreateReportUseCase:
    report_repo: ReportRepository
    client_repo: ClientRepository

    async def execute(
        self,
        tenant_id: UUID,
        created_by: UUID,
        request: CreateReportRequest,
    ) -> ReportResponse:
        client_id = UUID(request.client_id)
        client = await self.client_repo.get_by_id(client_id)

        if client is None:
            raise ClientNotFoundError(f"Client {client_id} not found")

        if client.tenant_id != tenant_id:
            raise ClientNotInTenantError("Client does not belong to this tenant")

        report = Report(
            tenant_id=tenant_id,
            client_id=client_id,
            created_by=created_by,
            report_type=request.report_type,
            period=request.period,
        )
        saved = await self.report_repo.save(report)

        logger.info(
            "report_created",
            report_id=str(saved.id),
            report_type=saved.report_type,
            client_id=str(client_id),
        )

        return _to_response(saved)


def _to_response(report: Report) -> ReportResponse:
    from src.application.dtos.report import ReportFileResponse, ReportResponse

    return ReportResponse(
        id=str(report.id),
        client_id=str(report.client_id),
        tenant_id=str(report.tenant_id),
        report_type=report.report_type,
        period=report.period,
        status=report.status,
        error_message=report.error_message,
        source_files=[
            ReportFileResponse(
                id=str(f.id),
                file_type=f.file_type,
                original_name=f.original_name,
                storage_key=f.storage_key,
            )
            for f in report.source_files
        ],
        output_files=[
            ReportFileResponse(
                id=str(f.id),
                file_type=f.file_type,
                original_name=f.original_name,
                storage_key=f.storage_key,
            )
            for f in report.output_files
        ],
        created_at=report.created_at.isoformat(),
        updated_at=report.updated_at.isoformat(),
    )
