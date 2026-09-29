import io
import json
import re
import zipfile
from collections import Counter
from datetime import date
from pathlib import PurePosixPath
from typing import Literal

from fastapi import Request
from pydantic import BaseModel, ValidationError
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.qa_reports.models import DailyReport
from app.modules.qa_reports.schemas import BackupReport, ItemInput, Schema
from app.modules.qa_reports.service import apply_items, owner_id

MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_REPORT_BYTES = 10 * 1024 * 1024
MAX_REPORTS = 1000
MONTH_FOLDER = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class ReportPreview(Schema):
    report_date: date
    month: str
    title: str
    activity_count: int
    total_hours: float
    already_exists: bool


class MonthPreview(Schema):
    month: str
    count: int


class ImportPreview(Schema):
    reports: list[ReportPreview]
    months: list[MonthPreview]
    total_reports: int
    new_reports: int
    existing_reports: int


class ImportResult(BaseModel):
    mode: Literal["missing", "overwrite"]
    added: int
    overwritten: int
    skipped: int


async def read_zip(request: Request) -> list[BackupReport]:
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_ARCHIVE_BYTES:
            raise AppError(413, "File ZIP maksimal 100 MB.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError):
        raise AppError(422, "File bukan arsip ZIP yang valid.") from None

    reports: list[BackupReport] = []
    uncompressed = 0
    try:
        with archive:
            entries = [entry for entry in archive.infolist() if not entry.is_dir()]
            if len(entries) > MAX_REPORTS:
                raise AppError(422, "ZIP maksimal berisi 1.000 file laporan.")
            for entry in entries:
                path = PurePosixPath(entry.filename)
                if "__MACOSX" in path.parts or path.name in {".DS_Store", "Thumbs.db"}:
                    continue
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in entry.filename
                    or len(path.parts) != 2
                    or not MONTH_FOLDER.fullmatch(path.parts[0])
                    or path.suffix.lower() != ".json"
                ):
                    raise AppError(
                        422,
                        "Struktur ZIP harus berupa folder YYYY-MM berisi file JSON laporan harian.",
                    )
                if entry.file_size > MAX_REPORT_BYTES:
                    raise AppError(413, "Setiap file laporan JSON maksimal 10 MB.")
                if uncompressed + entry.file_size > MAX_ARCHIVE_BYTES:
                    raise AppError(413, "Total isi ZIP maksimal 100 MB.")
                with archive.open(entry) as source_file:
                    raw = source_file.read(MAX_REPORT_BYTES + 1)
                if len(raw) > MAX_REPORT_BYTES:
                    raise AppError(413, "Setiap file laporan JSON maksimal 10 MB.")
                uncompressed += len(raw)
                if uncompressed > MAX_ARCHIVE_BYTES:
                    raise AppError(413, "Total isi ZIP maksimal 100 MB.")
                try:
                    payload = json.loads(raw)
                    if isinstance(payload, dict) and "report" in payload:
                        payload = payload["report"]
                    report = BackupReport.model_validate(payload)
                except (json.JSONDecodeError, ValidationError, UnicodeDecodeError):
                    raise AppError(
                        422,
                        f"File {entry.filename} bukan JSON laporan QA yang valid.",
                    ) from None
                if report.report_date.strftime("%Y-%m") != path.parts[0]:
                    raise AppError(
                        422,
                        f"Tanggal laporan pada {entry.filename} tidak cocok dengan folder bulannya.",
                    )
                reports.append(report)
    except (zipfile.BadZipFile, RuntimeError, OSError):
        raise AppError(422, "Isi arsip ZIP rusak atau tidak lengkap.") from None

    dates = [report.report_date for report in reports]
    if len(dates) != len(set(dates)):
        raise AppError(422, "ZIP memiliki lebih dari satu laporan untuk tanggal yang sama.")
    return sorted(reports, key=lambda report: report.report_date)


async def preview(db: AsyncSession, reports: list[BackupReport]) -> ImportPreview:
    dates = [report.report_date for report in reports]
    existing = set(
        await db.scalars(
            select(DailyReport.report_date).where(
                DailyReport.account_id == owner_id(db),
                DailyReport.report_date.in_(dates),
            )
        )
    )
    month_counts = Counter(report.report_date.strftime("%Y-%m") for report in reports)
    return ImportPreview(
        reports=[
            ReportPreview(
                report_date=report.report_date,
                month=report.report_date.strftime("%Y-%m"),
                title=report.title,
                activity_count=len(report.items),
                total_hours=round(
                    sum(item.duration_hours or 0 for item in report.items), 2
                ),
                already_exists=report.report_date in existing,
            )
            for report in reports
        ],
        months=[MonthPreview(month=month, count=count) for month, count in sorted(month_counts.items())],
        total_reports=len(reports),
        new_reports=len(reports) - sum(report.report_date in existing for report in reports),
        existing_reports=sum(report.report_date in existing for report in reports),
    )


async def restore(
    db: AsyncSession,
    reports: list[BackupReport],
    *,
    mode: Literal["missing", "overwrite"],
) -> ImportResult:
    dates = [report.report_date for report in reports]
    existing = set(
        await db.scalars(
            select(DailyReport.report_date).where(
                DailyReport.account_id == owner_id(db),
                DailyReport.report_date.in_(dates),
            )
        )
    )
    replacing = existing if mode == "overwrite" else set()
    if replacing:
        await db.execute(
            delete(DailyReport).where(
                DailyReport.account_id == owner_id(db),
                DailyReport.report_date.in_(replacing),
            )
        )
    selected = [report for report in reports if mode == "overwrite" or report.report_date not in existing]
    for source in selected:
        report = DailyReport(
            account_id=owner_id(db),
            title=source.title,
            report_date=source.report_date,
            author_name=source.author_name,
            status=source.status,
            version=source.version,
            updated_at=source.updated_at,
            slack_sent_at=source.slack_sent_at,
            email_sent_at=source.email_sent_at,
            template_id=None,
            template_name=source.template_name,
            template_body=source.template_body,
            template_values=source.template_values,
            items=[],
        )
        apply_items(
            report,
            [ItemInput.model_validate(item.model_dump(exclude={"id", "sort_order"})) for item in source.items],
        )
        db.add(report)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Laporan berubah selama import. Tidak ada data yang diimport; coba lagi.") from None
    overwritten = len(existing) if mode == "overwrite" else 0
    return ImportResult(
        mode=mode,
        added=len(selected) - overwritten,
        overwritten=overwritten,
        skipped=len(existing) if mode == "missing" else 0,
    )
