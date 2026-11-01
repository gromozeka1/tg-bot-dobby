"""Track notification retry timing.

Revision ID: 9f8c3d2a1b70
Revises: 1d2f7a454279
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9f8c3d2a1b70"
down_revision: str | None = "1d2f7a454279"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notification_log",
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("notification_log", "last_attempt_at")
