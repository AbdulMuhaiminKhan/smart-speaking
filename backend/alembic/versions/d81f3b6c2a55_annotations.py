"""time-pinned notes on a session's video

Revision ID: d81f3b6c2a55
Revises: c4d2a7e91f10
Create Date: 2026-11-14 15:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d81f3b6c2a55"
down_revision: str | None = "c4d2a7e91f10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "annotations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("t", sa.Float(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["practice_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_annotations_session_id", "annotations", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_annotations_session_id", table_name="annotations")
    op.drop_table("annotations")
