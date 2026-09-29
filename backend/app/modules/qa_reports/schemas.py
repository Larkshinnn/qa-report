from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.modules.qa_reports.templates import validate_body

TemplateValues = dict[
    Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,49}$")],
    Annotated[str, Field(max_length=10000)],
]


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True, extra="forbid")


class LinkInput(Schema):
    url: str = Field(min_length=1, max_length=4096)
    label: str | None = Field(default=None, max_length=255)


class LinkOutput(LinkInput):
    id: UUID


class ItemInput(Schema):
    id: UUID | None = None
    # Required fields depend on the saved template, checked by the service.
    activity_code: str = Field(default="", max_length=100)
    environment: str = Field(default="Dev", max_length=50)
    result: str = Field(default="", max_length=50)
    current_status: str | None = Field(default=None, max_length=100)
    current_issue: str | None = Field(default=None, max_length=10000)
    duration_hours: float | None = Field(default=None, ge=0)
    obstacle: str | None = Field(default=None, max_length=10000)
    next_step: str | None = Field(default=None, max_length=10000)
    pic_guidance: str | None = Field(default=None, max_length=10000)
    deliverable: str | None = Field(default=None, max_length=10000)
    links: list[LinkInput] = Field(default_factory=list, max_length=50)
    template_values: TemplateValues = Field(default_factory=dict, max_length=30)


class ItemOutput(ItemInput):
    id: UUID
    sort_order: int
    # Identifiers for links are not required for report editing; links are value objects.


class ReportCreate(Schema):
    report_date: date
    title: str = Field(min_length=1, max_length=255)
    author_name: str | None = Field(default=None, max_length=255)
    template_id: UUID | None = None

    @field_validator("report_date")
    @classmethod
    def supported_date(cls, value: date) -> date:
        if not 1900 <= value.year <= 2100:
            raise ValueError("Use a date between 1900 and 2100")
        return value


class ReportDraftCreate(ReportCreate):
    items: list[ItemInput] = Field(default_factory=list, max_length=500)
    template_values: TemplateValues = Field(default_factory=dict, max_length=30)


class ReportSave(ReportCreate):
    version: int = Field(ge=1)
    items: list[ItemInput] = Field(max_length=500)
    template_values: TemplateValues = Field(default_factory=dict, max_length=30)


class ReportOutput(ReportCreate):
    id: UUID
    status: Literal["draft", "finalized", "sent"]
    version: int
    items: list[ItemOutput]
    slack_sent_at: datetime | None
    email_sent_at: datetime | None
    updated_at: datetime
    template_name: str | None = None
    template_body: str | None = None
    template_values: TemplateValues = Field(default_factory=dict, max_length=30)

    @field_validator("template_body")
    @classmethod
    def valid_snapshot(cls, value: str | None) -> str | None:
        return validate_body(value) if value is not None else None


class ReportSummary(ReportCreate):
    id: UUID
    status: str
    item_count: int


class ReportPage(Schema):
    reports: list[ReportSummary]
    total: int
    page: int
    page_size: int


class VersionInput(Schema):
    version: int = Field(ge=1)


class Preview(Schema):
    title: str
    slack: str
    html: str
    markdown: str
    slack_mrkdwn: str


class BackupReport(ReportOutput):
    version: int = Field(ge=1)
    items: list[ItemOutput] = Field(max_length=500)


class TemplateCreate(Schema):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    body: str = Field(min_length=1, max_length=20000)


class TemplateUpdate(TemplateCreate):
    expected_updated_at: datetime


class TemplateOutput(TemplateCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
    usage_count: int = 0

    @field_validator("body")
    @classmethod
    def valid_body(cls, value: str) -> str:
        return validate_body(value)


class ReportBackup(Schema):
    format: Literal["qa-portal-reports"]
    schema_version: Literal[1, 2, 3, 4]
    exported_at: datetime
    reports: list[BackupReport] = Field(max_length=1000)
    templates: list[TemplateOutput] = Field(default_factory=list, max_length=100)

    @field_validator("templates")
    @classmethod
    def unique_templates(cls, value: list[TemplateOutput]) -> list[TemplateOutput]:
        if len({entry.name for entry in value}) != len(value) or len(
            {entry.id for entry in value}
        ) != len(value):
            raise ValueError("Duplicate templates in backup")
        return value

    @field_validator("reports")
    @classmethod
    def unique_dates(cls, value: list[BackupReport]) -> list[BackupReport]:
        dates = [report.report_date for report in value]
        if len(dates) != len(set(dates)):
            raise ValueError("Duplicate report dates in backup")
        return value


class RestoreResult(Schema):
    restored: int
    skipped: int


class SendInput(VersionInput):
    channel: Literal["slack", "email"]
    recipient: EmailStr | None = None


class DeliveryOptions(Schema):
    slack: bool
    email: bool


class CountGroup(Schema):
    label: str
    count: int


class DayCount(Schema):
    date: date
    count: int


class MonthlyMetrics(Schema):
    month: str
    total: int
    pass_rate: float
    issue_count: int
    repeated_entries: int
    total_hours: float
    hours_target: int = 160
    hours_target_met: bool
    environments: list[CountGroup]
    results: list[CountGroup]
    trend: list[DayCount]


class WorkspaceUserSummary(Schema):
    account_id: UUID
    display_name: str
    email: str
    report_dates: list[date]
    report_count: int
    activity_count: int
    total_hours: float
    pass_rate: float
    issue_count: int


class WorkspaceSummary(Schema):
    month: str
    hours_target: int = 160
    users: list[WorkspaceUserSummary]


class CsvPreviewRow(Schema):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=False, extra="forbid")

    row_id: str
    date: date
    title: str
    activity: str
    environment: str
    result: str
    current_status: str
    current_issue: str
    coverage_links: str
    duration_hours: float | None
    obstacle: str
    next_step: str
    pic_guidance: str
    deliverable: str
