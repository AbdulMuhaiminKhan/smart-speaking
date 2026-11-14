"""practice modes (impromptu, elevator pitch, interview, table topics) and prompts

Revision ID: c4d2a7e91f10
Revises: 6ea139879667
Create Date: 2026-11-14 13:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c4d2a7e91f10"
down_revision: str | None = "6ea139879667"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JsonType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("practice_sessions") as batch:
        # The mode was stored as VARCHAR(11); new names like "elevator_pitch" are longer.
        batch.alter_column("mode", type_=sa.String(length=32), existing_type=sa.String(length=11))
        batch.add_column(sa.Column("prompts", JsonType, nullable=False, server_default="[]"))


def downgrade() -> None:
    with op.batch_alter_table("practice_sessions") as batch:
        batch.drop_column("prompts")
        batch.alter_column("mode", type_=sa.String(length=11), existing_type=sa.String(length=32))
