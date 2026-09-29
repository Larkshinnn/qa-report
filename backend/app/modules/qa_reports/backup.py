from dataclasses import dataclass
from datetime import UTC, datetime
import io
from uuid import uuid4
import zipfile

from fastapi import Request
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.modules.qa_reports.models import DailyReport, ReportItem, ReportTemplate
from app.modules.qa_reports.schemas import (
    BackupReport,
    ItemInput,
    ReportBackup,
    RestoreResult,
    TemplateOutput,
)
from app.modules.qa_reports.service import apply_items, owner_id

MAX_BACKUP_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class BackupComparison:
    existing_reports: int
    existing_templates: int
    new_reports: int
    new_templates: int


async def compare_backup(db: AsyncSession, backup: ReportBackup) -> BackupComparison:
    dates = [report.report_date for report in backup.reports]
    names = [template.name for template in backup.templates]
    matching_reports = (
        await db.scalar(
            select(func.count())
            .select_from(DailyReport)
            .where(
                DailyReport.account_id == owner_id(db),
                DailyReport.report_date.in_(dates),
            )
        )
        if dates
        else 0
    )
    matching_templates = (
        await db.scalar(
            select(func.count())
            .select_from(ReportTemplate)
            .where(ReportTemplate.account_id == owner_id(db), ReportTemplate.name.in_(names))
        )
        if names
        else 0
    )
    return BackupComparison(
        existing_reports=await db.scalar(
            select(func.count())
            .select_from(DailyReport)
            .where(DailyReport.account_id == owner_id(db))
        )
        or 0,
        existing_templates=await db.scalar(
            select(func.count())
            .select_from(ReportTemplate)
            .where(ReportTemplate.account_id == owner_id(db))
        )
        or 0,
        new_reports=len(backup.reports) - (matching_reports or 0),
        new_templates=len(backup.templates) - (matching_templates or 0),
    )


async def export_backup(db: AsyncSession) -> str:
    # Lock parent rows while loading their children, like the editor does for mutations.
    reports = (
        await db.scalars(
            select(DailyReport)
            .where(DailyReport.account_id == owner_id(db))
            .order_by(DailyReport.report_date)
            .limit(1001)
            .options(selectinload(DailyReport.items).selectinload(ReportItem.links))
            .with_for_update()
        )
    ).all()
    if len(reports) > 1000:
        raise AppError(
            413,
            "Backup JSON dibatasi 1.000 laporan. "
            "Gunakan backup PostgreSQL untuk arsip lebih besar.",
        )
    backup = ReportBackup(
        format="qa-portal-reports",
        schema_version=4,
        exported_at=datetime.now(UTC),
        reports=[BackupReport.model_validate(report) for report in reports],
        templates=[
            TemplateOutput.model_validate(template)
            for template in (
                await db.scalars(
                    select(ReportTemplate)
                    .where(ReportTemplate.account_id == owner_id(db))
                    .order_by(ReportTemplate.name)
                )
            ).all()
        ],
    ).model_dump_json()
    if len(backup.encode("utf-8")) > MAX_BACKUP_BYTES:
        raise AppError(
            413, "Backup melebihi 10 MB. Gunakan backup PostgreSQL untuk arsip lebih besar."
        )
    return backup


def export_monthly_zip(backup_json: str) -> bytes:
    backup = ReportBackup.model_validate_json(backup_json)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for report in backup.reports:
            folder = report.report_date.strftime("%Y-%m")
            archive.writestr(
                f"{folder}/{report.report_date.isoformat()}.json",
                report.model_dump_json(),
            )
    return output.getvalue()


async def read_backup(request: Request) -> ReportBackup:
    # Bound the stream before parsing JSON, including requests without Content-Length.
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_BACKUP_BYTES:
            raise AppError(413, "File backup maksimal 10 MB.")
    try:
        return ReportBackup.model_validate_json(data)
    except ValidationError:
        raise AppError(
            422, "Backup tidak valid. Gunakan file JSON backup QA Reports versi 1, 2, 3, atau 4."
        ) from None


async def restore_backup(
    db: AsyncSession, backup: ReportBackup, *, commit: bool = True
) -> RestoreResult:
    templates_by_name = {
        template.name: template
        for template in (
            await db.scalars(
                select(ReportTemplate).where(ReportTemplate.account_id == owner_id(db))
            )
        ).all()
    }
    template_ids = {}
    for source in backup.templates:
        template = templates_by_name.get(source.name)
        if template is None:
            if len(templates_by_name) >= 100:
                raise AppError(422, "Pemulihan melebihi batas 100 template.")
            template = ReportTemplate(
                id=uuid4(),
                account_id=owner_id(db),
                name=source.name,
                description=source.description,
                body=source.body,
            )
            templates_by_name[template.name] = template
            db.add(template)
        template_ids[source.id] = template.id
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise AppError(
            409, "Template berubah selama pemulihan. Tidak ada data dipulihkan; coba lagi."
        ) from None
    dates = {entry.report_date for entry in backup.reports}
    existing = set(
        await db.scalars(
            select(DailyReport.report_date).where(
                DailyReport.account_id == owner_id(db),
                DailyReport.report_date.in_(dates),
            )
        )
    )
    restored = 0
    for entry in backup.reports:
        if entry.report_date in existing:
            continue
        report = DailyReport(
            account_id=owner_id(db),
            title=entry.title,
            report_date=entry.report_date,
            author_name=entry.author_name,
            status=entry.status,
            version=entry.version,
            updated_at=entry.updated_at,
            slack_sent_at=entry.slack_sent_at,
            email_sent_at=entry.email_sent_at,
            template_id=template_ids.get(entry.template_id) if entry.template_id else None,
            template_name=entry.template_name,
            template_body=entry.template_body,
            template_values=entry.template_values,
            items=[],
        )
        # Restored records get new identities. Backup IDs can never update existing rows.
        apply_items(
            report,
            [
                ItemInput.model_validate(item.model_dump(exclude={"id", "sort_order"}))
                for item in entry.items
            ],
        )
        db.add(report)
        restored += 1
    try:
        if commit:
            await db.commit()
        else:
            await db.flush()
    except IntegrityError:
        await db.rollback()
        raise AppError(
            409, "Tanggal laporan berubah selama pemulihan. Tidak ada data dipulihkan; coba lagi."
        ) from None
    return RestoreResult(restored=restored, skipped=len(existing))


async def overwrite_backup(
    db: AsyncSession, backup: ReportBackup, *, commit: bool = True
) -> RestoreResult:
    await db.execute(delete(DailyReport).where(DailyReport.account_id == owner_id(db)))
    await db.execute(delete(ReportTemplate).where(ReportTemplate.account_id == owner_id(db)))
    await db.flush()
    return await restore_backup(db, backup, commit=commit)
