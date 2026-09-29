from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DailyReport(Base):
    __tablename__ = "daily_reports"
    __table_args__ = (
        CheckConstraint("status IN ('draft','finalized','sent')", name="ck_daily_report_status"),
        Index("ix_daily_reports_account_date", "account_id", "report_date"),
    )
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    report_date: Mapped[date] = mapped_column(Date)
    title: Mapped[str] = mapped_column(String(255), server_default="Daily QA Report")
    author_name: Mapped[str | None] = mapped_column(String(255))
    template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("report_templates.id", ondelete="SET NULL"), index=True
    )
    template_name: Mapped[str | None] = mapped_column(String(100))
    template_body: Mapped[str | None] = mapped_column(Text)
    template_values: Mapped[dict[str, str]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    version: Mapped[int] = mapped_column(default=1, server_default="1")
    slack_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    items: Mapped[list[ReportItem]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="ReportItem.sort_order",
    )


class ReportTemplate(Base):
    __tablename__ = "report_templates"
    __table_args__ = (Index("ix_report_templates_account_name", "account_id", "name", unique=True),)
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ReportItem(Base):
    __tablename__ = "report_items"
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    daily_report_id: Mapped[UUID] = mapped_column(
        ForeignKey("daily_reports.id", ondelete="CASCADE"), index=True
    )
    activity_code: Mapped[str] = mapped_column(String(100), index=True)
    environment: Mapped[str] = mapped_column(String(50), index=True)
    result: Mapped[str] = mapped_column(String(50), index=True)
    current_status: Mapped[str | None] = mapped_column(String(100))
    current_issue: Mapped[str | None] = mapped_column(Text)
    duration_hours: Mapped[float | None] = mapped_column(Float)
    obstacle: Mapped[str | None] = mapped_column(Text)
    next_step: Mapped[str | None] = mapped_column(Text)
    pic_guidance: Mapped[str | None] = mapped_column(Text)
    deliverable: Mapped[str | None] = mapped_column(Text)
    template_values: Mapped[dict[str, str]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    report: Mapped[DailyReport] = relationship(back_populates="items", lazy="raise")
    links: Mapped[list[ReportItemLink]] = relationship(
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="ReportItemLink.created_at, ReportItemLink.id",
    )


class ReportItemLink(Base):
    __tablename__ = "report_item_links"
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    report_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("report_items.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text)
    label: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
