"""user badges and ban

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-24

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # префиксы на профилях: кто выдал и когда
    op.create_table(
        "user_badges",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_user_badges_user_id_users"),
            nullable=False,
        ),
        sa.Column("badge", sa.String(length=30), nullable=False),
        sa.Column("granted_by", sa.Uuid(), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_badges")),
        sa.UniqueConstraint("user_id", "badge", name=op.f("uq_user_badges_user_id")),
    )
    op.create_index(op.f("ix_user_badges_user_id"), "user_badges", ["user_id"])

    op.add_column(
        "users", sa.Column("is_banned", sa.Boolean(), server_default=sa.false(), nullable=False)
    )


def downgrade() -> None:
    op.drop_column("users", "is_banned")
    op.drop_index(op.f("ix_user_badges_user_id"), table_name="user_badges")
    op.drop_table("user_badges")
