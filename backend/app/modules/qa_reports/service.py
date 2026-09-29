import calendar
import csv
import io
from datetime import date
from html import escape
from typing import Literal
from uuid import UUID

# openpyxl does not ship type hints.
from openpyxl import Workbook  # type: ignore[import-untyped]
from openpyxl.styles import Alignment, Font, PatternFill  # type: ignore[import-untyped]
from sqlalchemy import distinct, func, select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.modules.qa_reports.models import DailyReport, ReportItem, ReportItemLink, ReportTemplate
from app.modules.qa_reports.schemas import (
    CountGroup,
    CsvPreviewRow,
    DayCount,
    ItemInput,
    MonthlyMetrics,
    Preview,
    ReportDraftCreate,
    ReportPage,
    ReportSave,
    ReportSummary,
    TemplateCreate,
    TemplateOutput,
    TemplateUpdate,
)
from app.modules.qa_reports.templates import (
    ACTIVITY_KEYS,
    activity_keys,
    custom_keys,
    normalize_body,
    render_body,
    validate_body,
)


def owner_id(db: AsyncSession) -> UUID:
    account_id = db.info.get("account_id")
    if not isinstance(account_id, UUID):
        raise RuntimeError("QA service requires an authenticated account")
    return account_id


def validate_template_body(body: str) -> None:
    try:
        validate_body(body)
    except ValueError as error:
        raise AppError(422, str(error)) from None


async def get_template(
    db: AsyncSession, template_id: UUID, *, lock: bool = False
) -> ReportTemplate:
    query = select(ReportTemplate).where(
        ReportTemplate.id == template_id,
        ReportTemplate.account_id == owner_id(db),
    )
    template = await db.scalar(query.with_for_update() if lock else query)
    if template is None:
        raise AppError(404, "Template laporan tidak ditemukan.")
    return template


async def list_templates(db: AsyncSession) -> list[TemplateOutput]:
    usage = (
        select(DailyReport.template_id, func.count(DailyReport.id).label("usage_count"))
        .where(
            DailyReport.account_id == owner_id(db),
            DailyReport.template_id.is_not(None),
        )
        .group_by(DailyReport.template_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(ReportTemplate, func.coalesce(usage.c.usage_count, 0))
            .outerjoin(usage, usage.c.template_id == ReportTemplate.id)
            .where(ReportTemplate.account_id == owner_id(db))
            .order_by(ReportTemplate.updated_at.desc(), ReportTemplate.name)
        )
    ).all()
    return [
        TemplateOutput(
            id=template.id,
            name=template.name,
            description=template.description,
            body=template.body,
            created_at=template.created_at,
            updated_at=template.updated_at,
            usage_count=count,
        )
        for template, count in rows
    ]


async def create_template(db: AsyncSession, body: TemplateCreate) -> TemplateOutput:
    validate_template_body(body.body)
    if (
        await db.scalar(
            select(func.count())
            .select_from(ReportTemplate)
            .where(ReportTemplate.account_id == owner_id(db))
        )
        or 0
    ) >= 100:
        raise AppError(422, "Maksimal 100 template. Hapus template yang tidak digunakan.")
    template = ReportTemplate(
        **{
            **body.model_dump(),
            "account_id": owner_id(db),
            "body": normalize_body(body.body),
        }
    )
    db.add(template)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Nama template sudah digunakan.") from None
    await db.refresh(template)
    return TemplateOutput.model_validate(template)


async def update_template(
    db: AsyncSession, template_id: UUID, body: TemplateUpdate
) -> TemplateOutput:
    validate_template_body(body.body)
    template = await get_template(db, template_id, lock=True)
    if template.updated_at != body.expected_updated_at:
        raise AppError(409, "Template berubah di tab lain. Salin perubahanmu, lalu muat ulang.")
    template.name, template.description, template.body = (
        body.name,
        body.description,
        normalize_body(body.body),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Nama template sudah digunakan.") from None
    await db.refresh(template)
    return TemplateOutput.model_validate(template)


async def delete_template(db: AsyncSession, template_id: UUID) -> None:
    template = await get_template(db, template_id)
    await db.delete(template)
    await db.commit()


async def snapshot_template(
    db: AsyncSession, template_id: UUID | None
) -> tuple[UUID | None, str | None, str | None]:
    if template_id is None:
        return None, None, None
    template = await get_template(db, template_id)
    return template.id, template.name, template.body


async def get_report(db: AsyncSession, report_id: UUID, *, lock: bool = False) -> DailyReport:
    query = (
        select(DailyReport)
        .where(DailyReport.id == report_id, DailyReport.account_id == owner_id(db))
        .options(selectinload(DailyReport.items).selectinload(ReportItem.links))
    )
    if lock:
        query = query.with_for_update()
    report = await db.scalar(query)
    if report is None:
        raise AppError(404, "Laporan tidak ditemukan.")
    return report


async def date_conflict(db: AsyncSession, report_date: date) -> None:
    existing = await db.scalar(
        select(DailyReport.id).where(
            DailyReport.account_id == owner_id(db),
            DailyReport.report_date == report_date,
        )
    )
    if existing is None:
        raise AppError(409, "Data laporan atau template berubah. Muat ulang sebelum menyimpan.")
    raise AppError(409, "Tanggal ini sudah memiliki laporan. Buka laporan yang ada.", existing)


async def create_report(db: AsyncSession, body: ReportDraftCreate) -> DailyReport:
    template_id, template_name, template_body = await snapshot_template(db, body.template_id)
    report = DailyReport(
        **body.model_dump(exclude={"items", "template_id"}),
        account_id=owner_id(db),
        template_id=template_id,
        template_name=template_name,
        template_body=template_body,
        items=[],
    )
    report.template_values = {
        key: value
        for key, value in body.template_values.items()
        if key in custom_keys(template_body or "")
    }
    apply_items(report, body.items)
    db.add(report)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        await date_conflict(db, body.report_date)
    return report


def check_version(report: DailyReport, version: int, *, draft: bool = True) -> None:
    if report.version != version:
        raise AppError(409, "Laporan berubah di tab lain. Muat ulang sebelum menyimpan.")
    if draft and report.status != "draft":
        raise AppError(409, "Laporan sudah dikunci dan tidak dapat diedit.")


def apply_items(report: DailyReport, entries: list[ItemInput]) -> None:
    fields = activity_keys(report.template_body) if report.template_body else list(ACTIVITY_KEYS)
    custom = set(fields) - ACTIVITY_KEYS
    existing = {item.id: item for item in report.items}
    ids = [item.id for item in entries if item.id is not None]
    if len(set(ids)) != len(ids) or any(item_id not in existing for item_id in ids):
        raise AppError(422, "Daftar aktivitas tidak valid untuk laporan ini.")
    updated: list[ReportItem] = []
    for order, entry in enumerate(entries):
        for field in ("activity_code", "environment", "result"):
            if field in fields and not getattr(entry, field):
                raise AppError(422, f"Aktivitas {order + 1}: {field} wajib diisi.")
        item = existing[entry.id] if entry.id else ReportItem(links=[])
        item.activity_code = entry.activity_code
        item.environment = (
            entry.environment
            if "environment" in entry.model_fields_set or "environment" in fields
            else ""
        )
        item.result = entry.result
        item.current_status = entry.current_status or entry.result
        item.current_issue = entry.current_issue or None
        item.duration_hours = entry.duration_hours
        item.obstacle = entry.obstacle or None
        item.next_step = entry.next_step or None
        item.pic_guidance = entry.pic_guidance or None
        item.deliverable = entry.deliverable or None
        if "template_values" in entry.model_fields_set or not entry.id:
            item.template_values = {
                key: value for key, value in entry.template_values.items() if key in custom
            }
        item.sort_order = order
        item.links = [ReportItemLink(**link.model_dump()) for link in entry.links]
        updated.append(item)
    report.items = updated


async def save_report(db: AsyncSession, report_id: UUID, body: ReportSave) -> DailyReport:
    report = await get_report(db, report_id, lock=True)
    check_version(report, body.version)
    if "template_id" in body.model_fields_set:
        report.template_id, report.template_name, report.template_body = await snapshot_template(
            db, body.template_id
        )
    report.title, report.report_date = body.title, body.report_date
    report.author_name = body.author_name
    apply_items(report, body.items)
    if "template_values" in body.model_fields_set or "template_id" in body.model_fields_set:
        values = (
            body.template_values
            if "template_values" in body.model_fields_set
            else report.template_values
        )
        report.template_values = {
            key: value
            for key, value in values.items()
            if key in custom_keys(report.template_body or "")
        }
    report.version += 1
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        await date_conflict(db, body.report_date)
    await db.refresh(report, ["updated_at"])
    return report


async def finalize_report(db: AsyncSession, report_id: UUID, version: int) -> DailyReport:
    report = await get_report(db, report_id, lock=True)
    check_version(report, version)
    if not report.items:
        raise AppError(422, "Tambahkan minimal satu aktivitas sebelum finalisasi.")
    report.status = "finalized"
    report.version += 1
    await db.commit()
    await db.refresh(report, ["updated_at"])
    return report


async def delete_report(db: AsyncSession, report_id: UUID, version: int) -> None:
    report = await get_report(db, report_id, lock=True)
    check_version(report, version, draft=False)
    await db.delete(report)
    await db.commit()


async def list_reports(
    db: AsyncSession,
    start: date | None,
    end: date | None,
    environment: str,
    result: str,
    search: str,
    page: int,
    page_size: int,
    order: Literal["asc", "desc"] = "desc",
) -> ReportPage:
    query = select(DailyReport).where(DailyReport.account_id == owner_id(db))
    if start:
        query = query.where(DailyReport.report_date >= start)
    if end:
        query = query.where(DailyReport.report_date <= end)
    if start and end and start > end:
        raise AppError(422, "Tanggal awal harus sebelum tanggal akhir.")
    if environment or result or search:
        matching = select(ReportItem.id).where(ReportItem.daily_report_id == DailyReport.id)
        if environment:
            matching = matching.where(ReportItem.environment == environment)
        if result:
            matching = matching.where(ReportItem.result == result)
        if search:
            matching = matching.where(ReportItem.activity_code.icontains(search, autoescape=True))
        query = query.where(matching.exists())
    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    count = (
        select(func.count(ReportItem.id))
        .where(ReportItem.daily_report_id == DailyReport.id)
        .correlate(DailyReport)
        .scalar_subquery()
    )
    rows = (
        await db.execute(
            query.add_columns(count)
            .order_by(
                DailyReport.report_date.asc() if order == "asc" else DailyReport.report_date.desc()
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return ReportPage(
        total=total,
        page=page,
        page_size=page_size,
        reports=[
            ReportSummary(
                id=report.id,
                report_date=report.report_date,
                title=report.title,
                author_name=report.author_name,
                status=report.status,
                item_count=item_count,
            )
            for report, item_count in rows
        ],
    )


def generate_preview(report: DailyReport) -> Preview:
    if report.template_body:
        return generate_template_preview(report)
    if not report.items:
        raise AppError(422, "Tambahkan aktivitas untuk membuat preview laporan.")
    formatted_date = (
        f"{report.report_date.strftime('%B')} {report.report_date.day}, {report.report_date.year}"
    )
    sections: list[tuple[str, list[str]]] = [
        (
            "Testing Summary:",
            [
                f"Activity: {i.activity_code}\nEnvironment: {i.environment}\nResult: {i.result}"
                for i in report.items
            ],
        )
    ]
    coverage = [
        f"Activity: {i.activity_code}\n" + "\n".join(link.url for link in i.links)
        for i in report.items
        if i.links
    ]
    if coverage:
        sections.append(("Test Coverage :", coverage))
    issues = [f"{i.activity_code}: {i.current_issue}" for i in report.items if i.current_issue]
    if issues:
        sections.append(("Current issues:", issues))
    statuses = [f"{i.activity_code}: {i.current_status or i.result}" for i in report.items]
    if statuses:
        sections.append(("Current Status:", statuses))
    blocks = [f"{report.title}\nDate: {formatted_date}"]
    slack_blocks = [f"*{escape(report.title, quote=False)}*\nDate: {formatted_date}"]
    markdown_blocks = [f"# {report.title}\nDate: {formatted_date}"]
    for heading, entries in sections:
        # Continuation lines stay grouped under their activity, including multiline notes.
        indented = [entry.replace("\n", "\n  ") for entry in entries]
        content = "\n".join(f"- {entry}" for entry in indented)
        blocks.append(f"{heading}\n{content}")
        markdown_blocks.append(f"## {heading}\n\n" + content.replace("\n", "  \n"))
        slack_blocks.append(
            f"*{heading}*\n" + "\n".join(f"• {escape(entry, quote=False)}" for entry in indented)
        )
    plain = "\n\n".join(blocks)
    # HTML contains escaped text only, never user-supplied markup.
    html = (
        '<!doctype html><html><head><meta charset="utf-8"></head><body>'
        '<div style="font-family:Arial,sans-serif;white-space:pre-wrap;line-height:1.6">'
        + escape(plain)
        + "</div></body></html>"
    )
    return Preview(
        title=report.title,
        slack=plain,
        html=html,
        markdown="\n\n".join(markdown_blocks),
        slack_mrkdwn="\n\n".join(slack_blocks),
    )


def generate_template_preview(report: DailyReport) -> Preview:
    """Render the saved template snapshot with report and activity values."""
    assert report.template_body is not None
    custom = set(custom_keys(report.template_body))
    activities = [
        {
            **{key: value for key, value in (item.template_values or {}).items() if key in custom},
            "activity_code": item.activity_code,
            "environment": item.environment,
            "result": item.result,
            "coverage_links": "\n".join(link.url for link in item.links),
            "current_issue": item.current_issue or "",
            "current_status": item.current_status or item.result,
        }
        for item in report.items
    ]
    report_values = {
        **(report.template_values or {}),
        "report_title": report.title,
        "report_date": (
            f"{report.report_date.strftime('%B')} "
            f"{report.report_date.day}, {report.report_date.year}"
        ),
        "author_name": report.author_name or "",
    }
    try:
        rendered = render_body(report.template_body, report_values, activities)
    except ValueError as error:
        raise AppError(422, str(error)) from None
    html = (
        '<!doctype html><html><head><meta charset="utf-8"></head><body>'
        '<div style="font-family:Arial,sans-serif;white-space:pre-wrap;line-height:1.6">'
        + escape(rendered)
        + "</div></body></html>"
    )
    return Preview(
        title=report.title,
        slack=rendered,
        html=html,
        markdown=rendered,
        slack_mrkdwn=escape(rendered, quote=False),
    )


def month_bounds(month: str) -> tuple[date, date]:
    try:
        year, number = map(int, month.split("-"))
        if not 1900 <= year <= 2100:
            raise ValueError
        start = date(year, number, 1)
        end = date(year, number, calendar.monthrange(year, number)[1])
    except ValueError:
        raise AppError(422, "Bulan tidak valid. Gunakan YYYY-MM antara 1900 dan 2100.") from None
    return start, end


async def monthly_metrics(db: AsyncSession, month: str) -> MonthlyMetrics:
    start, end = month_bounds(month)
    query = (
        select(ReportItem)
        .join(DailyReport)
        .where(
            DailyReport.account_id == owner_id(db),
            DailyReport.report_date.between(start, end),
        )
    )
    entries = query.subquery()
    total, passed, issues, with_result, with_code = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(entries.c.result == "Pass"),
                func.count().filter(func.length(func.trim(entries.c.current_issue)) > 0),
                func.count().filter(entries.c.result != ""),
                func.count().filter(entries.c.activity_code != ""),
            ).select_from(entries)
        )
    ).one()
    environments = (
        await db.execute(
            select(entries.c.environment, func.count())
            .group_by(entries.c.environment)
            .order_by(entries.c.environment)
        )
    ).all()
    results = (
        await db.execute(
            select(entries.c.result, func.count())
            .group_by(entries.c.result)
            .order_by(entries.c.result)
        )
    ).all()
    days: dict[date, int] = {
        day: count
        for day, count in (
            await db.execute(
                select(DailyReport.report_date, func.count(ReportItem.id))
                .join(ReportItem)
                .where(
                    DailyReport.account_id == owner_id(db),
                    DailyReport.report_date.between(start, end),
                )
                .group_by(DailyReport.report_date)
            )
        ).all()
    }
    unique = (
        await db.scalar(
            select(
                func.count(
                    distinct(tuple_(entries.c.daily_report_id, entries.c.activity_code))
                ).filter(entries.c.activity_code != "")
            ).select_from(entries)
        )
        or 0
    )
    return MonthlyMetrics(
        month=month,
        total=total,
        pass_rate=round(passed / with_result * 100, 1) if with_result else 0,
        issue_count=issues,
        repeated_entries=with_code - unique,
        environments=[
            CountGroup(label=label or "Tidak diisi", count=count) for label, count in environments
        ],
        results=[CountGroup(label=label or "Tidak diisi", count=count) for label, count in results],
        trend=[
            DayCount(
                date=date(start.year, start.month, day),
                count=days.get(date(start.year, start.month, day), 0),
            )
            for day in range(1, end.day + 1)
        ],
    )


def csv_cell(value: str | None) -> str:
    text = value or ""
    stripped = text.lstrip()
    dangerous = stripped.startswith(("=", "+", "@")) or (
        stripped.startswith("-") and stripped[1:2].isdigit()
    )
    return "'" + text if dangerous else text


async def monthly_csv_rows(db: AsyncSession, month: str) -> list[CsvPreviewRow]:
    start, end = month_bounds(month)
    reports = (
        await db.scalars(
            select(DailyReport)
            .where(
                DailyReport.account_id == owner_id(db),
                DailyReport.report_date.between(start, end),
            )
            .options(selectinload(DailyReport.items).selectinload(ReportItem.links))
            .order_by(DailyReport.report_date.asc(), DailyReport.id)
        )
    ).all()
    return [
        CsvPreviewRow(
            row_id=f"{report.id}:{item.id}",
            date=report.report_date,
            title=report.title,
            activity=item.activity_code,
            environment=item.environment,
            result=item.result,
            current_status=item.current_status or "",
            current_issue=item.current_issue or "",
            coverage_links="\n".join(link.url for link in item.links),
            duration_hours=item.duration_hours,
            obstacle=item.obstacle or "",
            next_step=item.next_step or "",
            pic_guidance=item.pic_guidance or "",
            deliverable=item.deliverable or "",
        )
        for report in reports
        for item in report.items
    ]


async def export_csv(db: AsyncSession, month: str) -> str:
    rows = await monthly_csv_rows(db, month)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "Date",
            "Title",
            "Activity",
            "Environment",
            "Result",
            "Current status",
            "Current issue",
            "Coverage links",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                str(row.date),
                *map(
                    csv_cell,
                    [
                        row.title,
                        row.activity,
                        row.environment,
                        row.result,
                        row.current_status,
                        row.current_issue,
                        row.coverage_links,
                    ],
                ),
            ]
        )
    return "\ufeff" + output.getvalue()


async def export_manmonth(db: AsyncSession, month: str) -> bytes:
    rows = await monthly_csv_rows(db, month)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Manmonth"
    sheet.append(
        [
            "No",
            "Tanggal",
            "Hari",
            "Durasi Pengerjaan (Hour)",
            "Ticket / Task Ref",
            "Task Summary (Progress)",
            "Kendala (Obstacle)",
            "Next Step / Action",
            "PIC / Guidance",
            "Notion / Reference Link",
            "Deliverable",
            "Status",
        ]
    )
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    for number, row in enumerate(rows, 1):
        sheet.append(
            [
                number,
                row.date,
                days[row.date.weekday()],
                row.duration_hours,
                csv_cell(row.activity),
                csv_cell(row.current_issue),
                csv_cell(row.obstacle),
                csv_cell(row.next_step),
                csv_cell(row.pic_guidance),
                csv_cell(row.coverage_links),
                csv_cell(row.deliverable),
                csv_cell(row.current_status),
            ]
        )
    header_fill = PatternFill("solid", fgColor="1F4E78")
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    widths = [6, 14, 12, 24, 22, 42, 32, 32, 24, 42, 28, 20]
    for column, width in zip(sheet.columns, widths, strict=True):
        sheet.column_dimensions[column[0].column_letter].width = width
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        row[1].number_format = "dd mmm yyyy"
        row[3].number_format = "0.00"
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()
