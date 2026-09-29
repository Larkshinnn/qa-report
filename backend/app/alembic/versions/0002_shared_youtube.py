"""Add encrypted shared YouTube channel connection."""

import sqlalchemy as sa
from alembic import op

revision = "0002_shared_youtube"
down_revision = "0001_standalone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "youtube_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channel_id", sa.String(255), nullable=False),
        sa.Column("uploads_playlist_id", sa.String(255), nullable=False),
        sa.Column("channel_title", sa.String(255), nullable=False),
        sa.Column("refresh_token_encrypted", sa.String(4096), nullable=False),
        sa.Column("connected_by", sa.String(320), nullable=False),
        sa.Column(
            "connected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("youtube_connections")
