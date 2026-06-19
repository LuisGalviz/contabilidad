from __future__ import annotations

import asyncio
import io
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.report import CreateReportRequest, ReportFileResponse, ReportListResponse, ReportResponse
from src.application.use_cases.reports.create_report import (
    ClientNotFoundError,
    ClientNotInTenantError,
    CreateReportUseCase,
)
from src.application.use_cases.reports.generate_report import GenerateReportUseCase
from src.domain.entities.report import Report, ReportType
from src.infrastructure.database.connection import get_session
from src.infrastructure.repositories.client_repository import SQLClientRepository
from src.infrastructure.repositories.report_repository import SQLReportRepository
from src.infrastructure.storage.minio_service import download_bytes
from src.presentation.middleware.auth import CurrentUser, require_contador

router = APIRouter()


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    background_tasks: BackgroundTasks,
    client_id: str = Form(...),
    report_type: ReportType = Form(...),
    period: str = Form(default=""),
    files: list[UploadFile] = File(...),
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> ReportResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    request = CreateReportRequest(client_id=client_id, report_type=report_type, period=period)
    use_case = CreateReportUseCase(
        report_repo=SQLReportRepository(session),
        client_repo=SQLClientRepository(session),
    )
    try:
        result = await use_case.execute(current.tenant_id, current.user_id, request)
        await session.commit()
    except ClientNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ClientNotInTenantError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    raw_files = [(f.filename or f"file_{i}.xlsx", await f.read()) for i, f in enumerate(files)]

    report_id = UUID(result.id)
    background_tasks.add_task(_run_generation, report_id, raw_files)

    return result


async def _run_generation(report_id: UUID, raw_files: list[tuple[str, bytes]]) -> None:
    from src.infrastructure.database.connection import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        repo = SQLReportRepository(session)
        report = await repo.get_by_id(report_id)
        if report is None:
            return
        use_case = GenerateReportUseCase(report_repo=repo)
        await use_case.execute(report, raw_files)
        await session.commit()


@router.get("", response_model=ReportListResponse)
async def list_reports(
    limit: int = 20,
    offset: int = 0,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> ReportListResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    repo = SQLReportRepository(session)
    reports = await repo.list_by_tenant(current.tenant_id, limit=limit, offset=offset)
    items = [_to_response(r) for r in reports]
    return ReportListResponse(items=items, total=len(items))


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> ReportResponse:
    repo = SQLReportRepository(session)
    report = await repo.get_by_id(UUID(report_id))
    if not report or report.tenant_id != current.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found")
    return _to_response(report)


@router.get("/{report_id}/download/{file_id}")
async def download_report_file(
    report_id: str,
    file_id: str,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    repo = SQLReportRepository(session)
    report = await repo.get_by_id(UUID(report_id))
    if not report or report.tenant_id != current.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found")

    output = {str(f.id): f for f in report.output_files}
    if file_id not in output:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="File not found")

    file_obj = output[file_id]
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, download_bytes, file_obj.storage_key)

    media_type = file_obj.file_type or "application/octet-stream"
    return StreamingResponse(
        io.BytesIO(data),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file_obj.original_name}"',
            "Content-Length": str(len(data)),
        },
    )


def _to_response(report: Report) -> ReportResponse:
    return ReportResponse(
        id=str(report.id),
        client_id=str(report.client_id),
        tenant_id=str(report.tenant_id),
        report_type=report.report_type,
        period=report.period,
        status=report.status,
        error_message=report.error_message,
        source_files=[
            ReportFileResponse(id=str(f.id), file_type=f.file_type, original_name=f.original_name, storage_key=f.storage_key)
            for f in report.source_files
        ],
        output_files=[
            ReportFileResponse(id=str(f.id), file_type=f.file_type, original_name=f.original_name, storage_key=f.storage_key)
            for f in report.output_files
        ],
        metadata=report.metadata or {},
        created_at=report.created_at.isoformat(),
        updated_at=report.updated_at.isoformat(),
    )
