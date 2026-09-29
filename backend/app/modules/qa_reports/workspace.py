from sqlalchemy import and_, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Account
from app.modules.qa_reports.models import DailyReport, ReportItem
from app.modules.qa_reports.schemas import WorkspaceSummary, WorkspaceUserSummary
from app.modules.qa_reports.service import month_bounds


async def workspace_summary(db: AsyncSession, month: str) -> WorkspaceSummary:
    start, end = month_bounds(month)
    report_join = and_(
        DailyReport.account_id == Account.id,
        DailyReport.report_date.between(start, end),
    )
    rows = (
        await db.execute(
            select(
                Account.id,
                Account.display_name,
                Account.email,
                func.array_agg(distinct(DailyReport.report_date))
                .filter(DailyReport.id.is_not(None))
                .label("report_dates"),
                func.count(distinct(DailyReport.id)).label("report_count"),
                func.count(ReportItem.id).label("activity_count"),
                func.coalesce(func.sum(ReportItem.duration_hours), 0).label("total_hours"),
                func.count().filter(ReportItem.result == "Pass").label("passed"),
                func.count().filter(ReportItem.result != "").label("with_result"),
                func.count()
                .filter(func.length(func.trim(ReportItem.current_issue)) > 0)
                .label("issue_count"),
            )
            .select_from(Account)
            .outerjoin(DailyReport, report_join)
            .outerjoin(ReportItem, ReportItem.daily_report_id == DailyReport.id)
            .group_by(Account.id, Account.display_name, Account.email)
            .order_by(Account.display_name, Account.email)
        )
    ).all()
    return WorkspaceSummary(
        month=month,
        users=[
            WorkspaceUserSummary(
                account_id=row.id,
                display_name=row.display_name,
                email=row.email,
                report_dates=sorted(row.report_dates or []),
                report_count=row.report_count,
                activity_count=row.activity_count,
                total_hours=round(float(row.total_hours), 2),
                pass_rate=(round(row.passed / row.with_result * 100, 1) if row.with_result else 0),
                issue_count=row.issue_count,
            )
            for row in rows
        ],
    )
