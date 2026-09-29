"""Add superadmin and workspace visibility controls."""

import sqlalchemy as sa
from alembic import op

revision = "0003_workspace_visibility"
down_revision = "0002_shared_youtube"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("is_superadmin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "accounts",
        sa.Column("workspace_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("accounts", "workspace_visible")
    op.drop_column("accounts", "is_superadmin")
