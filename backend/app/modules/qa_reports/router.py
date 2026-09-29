from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from app.core.auth import OwnedDb, require_user
from app.modules.qa_reports import backup, delivery, service
from app.modules.qa_reports.workspace import workspace_summary
from app.modules.qa_reports.schemas import (
    CsvPreviewRow,
    DeliveryOptions,
    MonthlyMetrics,
    Preview,
    ReportDraftCreate,
    ReportOutput,
    ReportPage,
    ReportSave,
    RestoreResult,
    SendInput,
    TemplateCreate,
    TemplateOutput,
    TemplateUpdate,
    VersionInput,
)

router = APIRouter(
    prefix="/api/qa-reports", tags=["qa_reports"], dependencies=[Depends(require_user)]
)


@router.get("")
async def history(
    db: OwnedDb,
    start: date | None = None,
    end: date | None = None,
    environment: str = "",
    result: str = "",
    search: str = "",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    order: Literal["asc", "desc"] = "desc",
) -> ReportPage:
    return await service.list_reports(
        db, start, end, environment, result, search, page, page_size, order
    )


@router.post("", status_code=201)
async def create(body: ReportDraftCreate, db: OwnedDb) -> ReportOutput:
    return ReportOutput.model_validate(await service.create_report(db, body))


@router.get("/templates")
async def templates(db: OwnedDb) -> list[TemplateOutput]:
    return await service.list_templates(db)


@router.post("/templates", status_code=201)
async def create_template(body: TemplateCreate, db: OwnedDb) -> TemplateOutput:
    return await service.create_template(db, body)


@router.put("/templates/{template_id}")
async def update_template(template_id: UUID, body: TemplateUpdate, db: OwnedDb) -> TemplateOutput:
    return await service.update_template(db, template_id, body)


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(template_id: UUID, db: OwnedDb) -> Response:
    await service.delete_template(db, template_id)
    return Response(status_code=204)


@router.get("/monthly")
async def monthly(
    db: OwnedDb, month: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$")]
) -> MonthlyMetrics:
    return await service.monthly_metrics(db, month)


@router.get("/workspace")
async def shared_workspace(db: OwnedDb, month: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$")]):
    return await workspace_summary(db, month)


@router.get("/monthly.csv")
async def csv_download(
    db: OwnedDb, month: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$")]
) -> Response:
    csv = await service.export_csv(db, month)
    return Response(
        csv,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="qa-reports-{month}.csv"'},
    )


@router.get("/monthly/rows")
async def csv_preview(
    db: OwnedDb, month: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$")]
) -> list[CsvPreviewRow]:
    return await service.monthly_csv_rows(db, month)


@router.get("/monthly.manmonth.xlsx")
async def manmonth_download(
    db: OwnedDb, month: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$")]
) -> Response:
    return Response(
        await service.export_manmonth(db, month),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="manmonth-{month}.xlsx"'},
    )


@router.get("/delivery-options")
async def options() -> DeliveryOptions:
    return delivery.delivery_options()


@router.get("/backup")
async def backup_download(db: OwnedDb) -> Response:
    return Response(
        await backup.export_backup(db),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="qa-reports-backup.json"',
        },
    )


@router.post("/restore")
async def restore(request: Request, db: OwnedDb) -> RestoreResult:
    return await backup.restore_backup(db, await backup.read_backup(request))


@router.delete("/{report_id}", status_code=204)
async def delete(report_id: UUID, db: OwnedDb, version: Annotated[int, Query(ge=1)]) -> Response:
    await service.delete_report(db, report_id, version)
    return Response(status_code=204)


@router.get("/{report_id}")
async def detail(report_id: UUID, db: OwnedDb) -> ReportOutput:
    return ReportOutput.model_validate(await service.get_report(db, report_id))


@router.put("/{report_id}")
async def save(report_id: UUID, body: ReportSave, db: OwnedDb) -> ReportOutput:
    return ReportOutput.model_validate(await service.save_report(db, report_id, body))


@router.post("/{report_id}/finalize")
async def finalize(report_id: UUID, body: VersionInput, db: OwnedDb) -> ReportOutput:
    return ReportOutput.model_validate(await service.finalize_report(db, report_id, body.version))


@router.get("/{report_id}/preview")
async def preview(report_id: UUID, db: OwnedDb) -> Preview:
    return service.generate_preview(await service.get_report(db, report_id))


@router.post("/{report_id}/send")
async def send(report_id: UUID, body: SendInput, db: OwnedDb) -> ReportOutput:
    return ReportOutput.model_validate(await delivery.send_report(db, report_id, body))
