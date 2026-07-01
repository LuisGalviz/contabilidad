from __future__ import annotations

from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.mapping_rule import (
    ClassificationHistoryListResponse,
    ClassificationHistoryResponse,
    MappingRuleListResponse,
    MappingRuleResponse,
    PUCAccountListResponse,
    PUCAccountResponse,
)
from src.application.dtos.purchase_invoice import (
    BulkClassifyRequest,
    CausationEntryLineResponse,
    CausationEntryListResponse,
    CausationEntryResponse,
    CausationGenerateRequest,
    CausationGenerateResponse,
    ClassifyInvoiceRequest,
    ImportBatchListResponse,
    ImportBatchResponse,
    RejectInvoiceRequest,
    SupplierInvoiceListResponse,
    SupplierInvoiceResponse,
)
from src.application.dtos.report import CreateReportRequest
from src.application.use_cases.purchases.confirm_classification import ConfirmInvoiceClassificationUseCase
from src.application.use_cases.purchases.create_import_batch import (
    ClientNotFoundError,
    ClientNotInTenantError,
    CreateImportBatchUseCase,
)
from src.application.use_cases.purchases.generate_causation_entries import (
    GenerateCausationEntriesUseCase,
    InvoiceNotClassifiedError,
)
from src.application.use_cases.purchases.process_import_batch import ProcessImportBatchUseCase
from src.application.use_cases.purchases.suggest_mapping import SuggestMappingUseCase
from src.application.use_cases.reports.create_report import CreateReportUseCase
from src.application.use_cases.reports.generate_report import GenerateReportUseCase
from src.domain.entities.causation_entry import CausationEntry
from src.domain.entities.classification_history import ClassificationHistoryEntry
from src.domain.entities.invoice_import_batch import InvoiceImportBatch
from src.domain.entities.mapping_rule import SupplierMappingRule
from src.domain.entities.report import ReportType
from src.domain.entities.supplier_invoice import InvoiceStatus, SupplierInvoice
from src.infrastructure.accounting.internal_accounting_system import InternalAccountingSystem
from src.infrastructure.database.connection import get_session
from src.infrastructure.repositories.causation_entry_repository import SQLCausationEntryRepository
from src.infrastructure.repositories.classification_history_repository import SQLClassificationHistoryRepository
from src.infrastructure.repositories.client_repository import SQLClientRepository
from src.infrastructure.repositories.import_batch_repository import SQLInvoiceImportBatchRepository
from src.infrastructure.repositories.mapping_rule_repository import SQLSupplierMappingRuleRepository
from src.infrastructure.repositories.puc_account_repository import SQLPUCAccountRepository
from src.infrastructure.repositories.report_repository import SQLReportRepository
from src.infrastructure.repositories.supplier_invoice_repository import SQLSupplierInvoiceRepository
from src.infrastructure.storage.minio_service import upload_bytes
from src.presentation.middleware.auth import CurrentUser, require_contador

logger = structlog.get_logger()

router = APIRouter()
puc_router = APIRouter()


# ── import batches ──────────────────────────────────────────────────────────


@router.post("/import-batches", response_model=ImportBatchResponse, status_code=status.HTTP_201_CREATED)
async def create_import_batch(
    background_tasks: BackgroundTasks,
    client_id: str = Form(...),
    file: UploadFile = File(...),
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> ImportBatchResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    file_bytes = await file.read()
    original_name = file.filename or "documentos_dian.xlsx"
    storage_key = f"purchases/{current.tenant_id}/{uuid4()}/{original_name}"
    upload_bytes(
        storage_key,
        file_bytes,
        file.content_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    use_case = CreateImportBatchUseCase(
        batch_repo=SQLInvoiceImportBatchRepository(session),
        client_repo=SQLClientRepository(session),
    )
    try:
        batch = await use_case.execute(current.tenant_id, current.user_id, UUID(client_id), storage_key, original_name)
        await session.commit()
    except ClientNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ClientNotInTenantError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    background_tasks.add_task(_run_import_processing, batch.id, file_bytes)
    return _batch_to_response(batch)


@router.get("/import-batches", response_model=ImportBatchListResponse)
async def list_import_batches(
    limit: int = 20,
    offset: int = 0,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> ImportBatchListResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    repo = SQLInvoiceImportBatchRepository(session)
    batches = await repo.list_by_tenant(current.tenant_id, limit=limit, offset=offset)
    items = [_batch_to_response(b) for b in batches]
    return ImportBatchListResponse(items=items, total=len(items))


@router.get("/import-batches/{batch_id}", response_model=ImportBatchResponse)
async def get_import_batch(
    batch_id: str,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> ImportBatchResponse:
    repo = SQLInvoiceImportBatchRepository(session)
    batch = await repo.get_by_id(UUID(batch_id))
    if not batch or batch.tenant_id != current.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Import batch not found")
    return _batch_to_response(batch)


async def _run_import_processing(batch_id: UUID, file_bytes: bytes) -> None:
    from src.infrastructure.database.connection import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        batch_repo = SQLInvoiceImportBatchRepository(session)
        batch = await batch_repo.get_by_id(batch_id)
        if batch is None:
            return

        mapping_rule_repo = SQLSupplierMappingRuleRepository(session)
        use_case = ProcessImportBatchUseCase(
            batch_repo=batch_repo,
            invoice_repo=SQLSupplierInvoiceRepository(session),
            mapping_rule_repo=mapping_rule_repo,
            suggest_mapping=SuggestMappingUseCase(mapping_rule_repo),
            history_repo=SQLClassificationHistoryRepository(session),
        )
        await use_case.execute(batch, file_bytes)
        await session.commit()


# ── invoices ─────────────────────────────────────────────────────────────────


@router.get("/invoices", response_model=SupplierInvoiceListResponse)
async def list_invoices(
    client_id: str,
    invoice_status: InvoiceStatus | None = Query(default=None, alias="status"),
    batch_id: str | None = None,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> SupplierInvoiceListResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    repo = SQLSupplierInvoiceRepository(session)
    if batch_id:
        invoices = [inv for inv in await repo.list_by_batch(UUID(batch_id)) if inv.tenant_id == current.tenant_id]
    else:
        invoices = await repo.list_by_client(current.tenant_id, UUID(client_id), invoice_status)
    return SupplierInvoiceListResponse(items=[_invoice_to_response(inv) for inv in invoices], total=len(invoices))


@router.get("/invoices/{invoice_id}", response_model=SupplierInvoiceResponse)
async def get_invoice(
    invoice_id: str,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> SupplierInvoiceResponse:
    repo = SQLSupplierInvoiceRepository(session)
    invoice = await repo.get_by_id(UUID(invoice_id))
    if not invoice or invoice.tenant_id != current.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return _invoice_to_response(invoice)


@router.post("/invoices/{invoice_id}/classify", response_model=SupplierInvoiceResponse)
async def classify_invoice(
    invoice_id: str,
    body: ClassifyInvoiceRequest,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> SupplierInvoiceResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    invoice_repo = SQLSupplierInvoiceRepository(session)
    existing = await invoice_repo.get_by_id(UUID(invoice_id))
    if not existing or existing.tenant_id != current.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    use_case = ConfirmInvoiceClassificationUseCase(
        invoice_repo=invoice_repo,
        mapping_rule_repo=SQLSupplierMappingRuleRepository(session),
        history_repo=SQLClassificationHistoryRepository(session),
    )
    invoice, _rule = await use_case.execute(
        UUID(invoice_id),
        body.account_code,
        UUID(body.cost_center_id) if body.cost_center_id else None,
        current.user_id,
    )
    await session.commit()
    return _invoice_to_response(invoice)


@router.post("/invoices/bulk-classify", response_model=SupplierInvoiceListResponse)
async def bulk_classify_invoices(
    body: BulkClassifyRequest,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> SupplierInvoiceListResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    invoice_repo = SQLSupplierInvoiceRepository(session)
    use_case = ConfirmInvoiceClassificationUseCase(
        invoice_repo=invoice_repo,
        mapping_rule_repo=SQLSupplierMappingRuleRepository(session),
        history_repo=SQLClassificationHistoryRepository(session),
    )
    cost_center_id = UUID(body.cost_center_id) if body.cost_center_id else None

    results: list[SupplierInvoice] = []
    for raw_id in body.invoice_ids:
        invoice_id = UUID(raw_id)
        existing = await invoice_repo.get_by_id(invoice_id)
        if not existing or existing.tenant_id != current.tenant_id:
            continue
        invoice, _rule = await use_case.execute(invoice_id, body.account_code, cost_center_id, current.user_id)
        results.append(invoice)

    await session.commit()
    return SupplierInvoiceListResponse(items=[_invoice_to_response(inv) for inv in results], total=len(results))


@router.post("/invoices/{invoice_id}/reject", response_model=SupplierInvoiceResponse)
async def reject_invoice(
    invoice_id: str,
    body: RejectInvoiceRequest,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> SupplierInvoiceResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    repo = SQLSupplierInvoiceRepository(session)
    invoice = await repo.get_by_id(UUID(invoice_id))
    if not invoice or invoice.tenant_id != current.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    invoice.reject(body.reason)
    await repo.save(invoice)
    await session.commit()
    return _invoice_to_response(invoice)


# ── causación ────────────────────────────────────────────────────────────────


@router.post("/causation/generate", response_model=CausationGenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_causation(
    background_tasks: BackgroundTasks,
    body: CausationGenerateRequest,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> CausationGenerateResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    client_repo = SQLClientRepository(session)
    client = await client_repo.get_by_id(UUID(body.client_id))
    if not client or client.tenant_id != current.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Client not found")

    invoice_ids = [UUID(i) for i in body.invoice_ids]
    background_tasks.add_task(
        _run_causation_generation, current.tenant_id, UUID(body.client_id), current.user_id, body.period, invoice_ids
    )
    return CausationGenerateResponse(entries=[], reports_triggered=True)


@router.get("/causation", response_model=CausationEntryListResponse)
async def list_causation_entries(
    client_id: str,
    period: str | None = None,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> CausationEntryListResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    repo = SQLCausationEntryRepository(session)
    entries = await repo.list_by_client(current.tenant_id, UUID(client_id), period)
    return CausationEntryListResponse(items=[_entry_to_response(e) for e in entries], total=len(entries))


async def _run_causation_generation(
    tenant_id: UUID,
    client_id: UUID,
    created_by: UUID,
    period: str,
    invoice_ids: list[UUID],
) -> None:
    """Generates causación for the given invoices (or all CLASSIFIED invoices
    for the period if none given), then — in the same background task,
    in-process — auto-generates the two purchases reports for that
    client/period. The user never triggers report generation directly; this
    is the one place it happens, right after causación completes.
    """
    from src.infrastructure.database.connection import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        invoice_repo = SQLSupplierInvoiceRepository(session)
        causation_repo = SQLCausationEntryRepository(session)
        client_repo = SQLClientRepository(session)

        target_ids = invoice_ids
        if not target_ids:
            invoices = await invoice_repo.list_by_client_and_period(tenant_id, client_id, period)
            target_ids = [inv.id for inv in invoices if inv.status == InvoiceStatus.CLASSIFIED]

        if not target_ids:
            logger.info("causation_generation_skipped_no_invoices", client_id=str(client_id), period=period)
            return

        accounting_system = InternalAccountingSystem(causation_repo)
        causation_use_case = GenerateCausationEntriesUseCase(invoice_repo=invoice_repo, accounting_system=accounting_system)
        try:
            await causation_use_case.execute(target_ids)
        except InvoiceNotClassifiedError as exc:
            logger.warning("causation_generation_partial_failure", client_id=str(client_id), error=str(exc))
        await session.commit()

        report_repo = SQLReportRepository(session)
        puc_repo = SQLPUCAccountRepository(session)
        report_use_case = CreateReportUseCase(report_repo=report_repo, client_repo=client_repo)
        generate_use_case = GenerateReportUseCase(
            report_repo=report_repo,
            client_repo=client_repo,
            invoice_repo=invoice_repo,
            causation_repo=causation_repo,
            puc_account_repo=puc_repo,
        )

        for report_type in (ReportType.PURCHASES_GENERAL, ReportType.PURCHASES_SECTOR):
            response = await report_use_case.execute(
                tenant_id,
                created_by,
                CreateReportRequest(client_id=str(client_id), report_type=report_type, period=period),
            )
            await session.commit()

            report = await report_repo.get_by_id(UUID(response.id))
            if report is None:
                continue
            await generate_use_case.execute(report, raw_files=[])
            await session.commit()


# ── mapping rules & PUC accounts ───────────────────────────────────────────


@router.get("/mapping-rules", response_model=MappingRuleListResponse)
async def list_mapping_rules(
    client_id: str,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> MappingRuleListResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    repo = SQLSupplierMappingRuleRepository(session)
    rules = await repo.list_by_client(current.tenant_id, UUID(client_id))
    return MappingRuleListResponse(items=[_rule_to_response(r) for r in rules])


@router.get("/mapping-rules/{rule_id}/history", response_model=ClassificationHistoryListResponse)
async def get_mapping_rule_history(
    rule_id: str,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> ClassificationHistoryListResponse:
    if not current.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tenant associated")

    repo = SQLClassificationHistoryRepository(session)
    entries = [e for e in await repo.list_by_rule(UUID(rule_id)) if e.tenant_id == current.tenant_id]
    return ClassificationHistoryListResponse(items=[_history_to_response(e) for e in entries])


@puc_router.get("/accounts", response_model=PUCAccountListResponse)
async def list_puc_accounts(
    account_class: str | None = None,
    search: str | None = None,
    current: CurrentUser = Depends(require_contador),
    session: AsyncSession = Depends(get_session),
) -> PUCAccountListResponse:
    repo = SQLPUCAccountRepository(session)
    accounts = await repo.list_active(account_class=account_class, search=search)
    return PUCAccountListResponse(
        items=[
            PUCAccountResponse(
                code=a.code, name=a.name, account_class=a.account_class, requires_cost_center=a.requires_cost_center
            )
            for a in accounts
        ]
    )


# ── response mappers ─────────────────────────────────────────────────────────


def _batch_to_response(batch: InvoiceImportBatch) -> ImportBatchResponse:
    return ImportBatchResponse(
        id=str(batch.id),
        client_id=str(batch.client_id),
        tenant_id=str(batch.tenant_id),
        original_name=batch.original_name,
        status=batch.status,
        total_rows=batch.total_rows,
        new_invoices=batch.new_invoices,
        duplicate_invoices=batch.duplicate_invoices,
        error_rows=batch.error_rows,
        error_message=batch.error_message,
        created_at=batch.created_at.isoformat(),
        updated_at=batch.updated_at.isoformat(),
    )


def _invoice_to_response(invoice: SupplierInvoice) -> SupplierInvoiceResponse:
    return SupplierInvoiceResponse(
        id=str(invoice.id),
        client_id=str(invoice.client_id),
        import_batch_id=str(invoice.import_batch_id),
        cufe=invoice.cufe,
        supplier_nit=invoice.supplier_nit,
        supplier_name=invoice.supplier_name,
        issue_date=invoice.issue_date.isoformat(),
        concept_description=invoice.concept_description,
        subtotal=invoice.subtotal,
        vat_amount=invoice.vat_amount,
        total_amount=invoice.total_amount,
        status=invoice.status,
        suggested_account_code=invoice.suggested_account_code,
        suggested_cost_center_id=str(invoice.suggested_cost_center_id) if invoice.suggested_cost_center_id else None,
        suggested_confidence=invoice.suggested_confidence,
        classification_source=invoice.classification_source,
        final_account_code=invoice.final_account_code,
        final_cost_center_id=str(invoice.final_cost_center_id) if invoice.final_cost_center_id else None,
        rejection_reason=invoice.rejection_reason,
    )


def _entry_to_response(entry: CausationEntry) -> CausationEntryResponse:
    return CausationEntryResponse(
        id=str(entry.id),
        client_id=str(entry.client_id),
        invoice_id=str(entry.invoice_id),
        entry_date=entry.entry_date.isoformat(),
        status=entry.status.value,
        external_reference=entry.external_reference,
        lines=[
            CausationEntryLineResponse(
                account_code=line.account_code,
                debit=line.debit,
                credit=line.credit,
                description=line.description,
                cost_center_id=str(line.cost_center_id) if line.cost_center_id else None,
            )
            for line in entry.lines
        ],
    )


def _rule_to_response(rule: SupplierMappingRule) -> MappingRuleResponse:
    return MappingRuleResponse(
        id=str(rule.id),
        client_id=str(rule.client_id),
        supplier_nit=rule.supplier_nit,
        concept_keywords=rule.concept_keywords,
        account_code=rule.account_code,
        cost_center_id=str(rule.cost_center_id) if rule.cost_center_id else None,
        confidence=rule.confidence,
        times_confirmed=rule.times_confirmed,
        times_corrected=rule.times_corrected,
        is_active=rule.is_active,
    )


def _history_to_response(entry: ClassificationHistoryEntry) -> ClassificationHistoryResponse:
    return ClassificationHistoryResponse(
        id=str(entry.id),
        invoice_id=str(entry.invoice_id),
        action=entry.action.value,
        account_code_before=entry.account_code_before,
        account_code_after=entry.account_code_after,
        rule_id=str(entry.rule_id) if entry.rule_id else None,
        user_id=str(entry.user_id) if entry.user_id else None,
        created_at=entry.created_at.isoformat(),
    )
