from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.report import Report, ReportFile, ReportStatus, ReportType
from src.domain.repositories.report_repository import ReportRepository
from src.infrastructure.database.models import ReportFileModel, ReportModel


class SQLReportRepository(ReportRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Report | None:
        result = await self._session.execute(
            select(ReportModel).options(selectinload(ReportModel.files)).where(ReportModel.id == id)
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_by_client(
        self,
        client_id: UUID,
        tenant_id: UUID,
        report_type: ReportType | None = None,
    ) -> list[Report]:
        q = (
            select(ReportModel)
            .options(selectinload(ReportModel.files))
            .where(ReportModel.client_id == client_id, ReportModel.tenant_id == tenant_id)
        )
        if report_type:
            q = q.where(ReportModel.report_type == report_type.value)
        result = await self._session.execute(q.order_by(ReportModel.created_at.desc()))
        return [_to_domain(row) for row in result.scalars()]

    async def list_by_tenant(self, tenant_id: UUID, limit: int = 20, offset: int = 0) -> list[Report]:
        result = await self._session.execute(
            select(ReportModel)
            .options(selectinload(ReportModel.files))
            .where(ReportModel.tenant_id == tenant_id)
            .order_by(ReportModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [_to_domain(row) for row in result.scalars()]

    async def save(self, report: Report) -> Report:
        existing = await self._session.execute(
            select(ReportModel).options(selectinload(ReportModel.files)).where(ReportModel.id == report.id)
        )
        row = existing.scalar_one_or_none()

        if row:
            row.status = report.status.value
            row.error_message = report.error_message
            row.metadata_ = report.metadata
            if report.period:
                row.period = report.period

            existing_file_ids = {f.id for f in row.files}
            for f in report.output_files:
                if f.id not in existing_file_ids:
                    self._session.add(ReportFileModel(
                        id=f.id,
                        report_id=row.id,
                        file_type=f.file_type,
                        storage_key=f.storage_key,
                        original_name=f.original_name,
                        role="output",
                    ))

            await self._session.flush()
            return report

        model = ReportModel(
            id=report.id,
            tenant_id=report.tenant_id,
            client_id=report.client_id,
            created_by=report.created_by,
            report_type=report.report_type.value,
            period=report.period,
            status=report.status.value,
            error_message=report.error_message,
            metadata_=report.metadata,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return report

    async def delete(self, id: UUID) -> None:
        row = await self._session.get(ReportModel, id)
        if row:
            await self._session.delete(row)
            await self._session.flush()


def _to_domain(model: ReportModel) -> Report:
    source_files = [
        ReportFile(
            id=f.id,
            report_id=f.report_id,
            file_type=f.file_type,
            storage_key=f.storage_key,
            original_name=f.original_name,
            created_at=f.created_at,
        )
        for f in model.files
        if f.role == "source"
    ]
    output_files = [
        ReportFile(
            id=f.id,
            report_id=f.report_id,
            file_type=f.file_type,
            storage_key=f.storage_key,
            original_name=f.original_name,
            created_at=f.created_at,
        )
        for f in model.files
        if f.role == "output"
    ]
    return Report(
        id=model.id,
        tenant_id=model.tenant_id,
        client_id=model.client_id,
        created_by=model.created_by,
        report_type=ReportType(model.report_type),
        period=model.period,
        status=ReportStatus(model.status),
        error_message=model.error_message,
        source_files=source_files,
        output_files=output_files,
        metadata=model.metadata_,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
