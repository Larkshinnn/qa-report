"""Create standalone multi-account QA Report schema."""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_standalone"
down_revision = None
branch_labels = None
depends_on = None


def uuid_pk() -> sa.Column[UUID]:
    return sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.func.gen_random_uuid())


def timestamps() -> list[sa.Column[datetime]]:
    return [
        sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
        for name in ("created_at", "updated_at")
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "accounts",
        uuid_pk(),
        sa.Column("google_sub", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(2048)),
        sa.Column(
            "last_login_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_accounts_google_sub", "accounts", ["google_sub"])
    op.create_index("ix_accounts_email", "accounts", ["email"])
    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column(
            "account_id",
            sa.UUID(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessions_account_id", "sessions", ["account_id"])
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    op.create_table(
        "report_templates",
        uuid_pk(),
        sa.Column(
            "account_id",
            sa.UUID(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(255)),
        sa.Column("body", sa.Text(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("account_id", "name", name="uq_report_templates_account_name"),
    )
    op.create_index("ix_report_templates_account_id", "report_templates", ["account_id"])
    op.create_table(
        "daily_reports",
        uuid_pk(),
        sa.Column(
            "account_id",
            sa.UUID(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, server_default="Daily QA Report"),
        sa.Column("author_name", sa.String(255)),
        sa.Column(
            "template_id", sa.UUID(), sa.ForeignKey("report_templates.id", ondelete="SET NULL")
        ),
        sa.Column("template_name", sa.String(100)),
        sa.Column("template_body", sa.Text()),
        sa.Column("template_values", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("slack_sent_at", sa.DateTime(timezone=True)),
        sa.Column("email_sent_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.UniqueConstraint("account_id", "report_date", name="uq_daily_reports_account_date"),
        sa.CheckConstraint("status IN ('draft','finalized','sent')", name="ck_daily_report_status"),
    )
    op.create_index("ix_daily_reports_account_id", "daily_reports", ["account_id"])
    op.create_index("ix_daily_reports_template_id", "daily_reports", ["template_id"])
    op.create_index("ix_daily_reports_account_date", "daily_reports", ["account_id", "report_date"])
    op.create_table(
        "report_items",
        uuid_pk(),
        sa.Column(
            "daily_report_id",
            sa.UUID(),
            sa.ForeignKey("daily_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("activity_code", sa.String(100), nullable=False),
        sa.Column("environment", sa.String(50), nullable=False),
        sa.Column("result", sa.String(50), nullable=False),
        sa.Column("current_status", sa.String(100)),
        sa.Column("current_issue", sa.Text()),
        sa.Column("duration_hours", sa.Float()),
        sa.Column("obstacle", sa.Text()),
        sa.Column("next_step", sa.Text()),
        sa.Column("pic_guidance", sa.Text()),
        sa.Column("deliverable", sa.Text()),
        sa.Column("template_values", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        *timestamps(),
    )
    for name in ("daily_report_id", "activity_code", "environment", "result"):
        op.create_index(f"ix_report_items_{name}", "report_items", [name])
    op.create_table(
        "report_item_links",
        uuid_pk(),
        sa.Column(
            "report_item_id",
            sa.UUID(),
            sa.ForeignKey("report_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("label", sa.String(255)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_report_item_links_report_item_id", "report_item_links", ["report_item_id"])
    op.execute("""CREATE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
        BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$ LANGUAGE plpgsql""")
    for table in ("report_templates", "daily_reports", "report_items"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    for table in (
        "report_item_links",
        "report_items",
        "daily_reports",
        "report_templates",
        "sessions",
        "accounts",
    ):
        op.drop_table(table)
    op.execute("DROP FUNCTION set_updated_at()")
