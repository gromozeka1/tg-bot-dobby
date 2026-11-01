"""Add group_members for passive member collection.

Revision ID: b3a7c1d9e5f2
Revises: 9f8c3d2a1b70
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b3a7c1d9e5f2"
down_revision: str | None = "9f8c3d2a1b70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "group_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chat_id", sa.Integer(), sa.ForeignKey("chats.id", ondelete="CASCADE")),
        sa.Column("tg_user_id", sa.BigInteger(), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("chat_id", "tg_user_id", name="uq_group_members"),
    )
    op.create_index("ix_group_members_chat_id", "group_members", ["chat_id"])


def downgrade() -> None:
    op.drop_index("ix_group_members_chat_id", table_name="group_members")
    op.drop_table("group_members")
