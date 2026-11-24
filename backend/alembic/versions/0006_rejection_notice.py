"""rejection notice flag

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-24

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # прототип уведомлений: одноразовый флаг что историю отклонили
    op.add_column(
        "users", sa.Column("has_rejection_notice", sa.Boolean(), server_default=sa.false(), nullable=False)
    )


def downgrade() -> None:
    op.drop_column("users", "has_rejection_notice")
