"""profile profession tag

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-21

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("profession_tag_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_user_profiles_profession_tag_id_tags",
        "user_profiles",
        "tags",
        ["profession_tag_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_user_profiles_profession_tag_id"), "user_profiles", ["profession_tag_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_profiles_profession_tag_id"), table_name="user_profiles")
    op.drop_constraint(
        "fk_user_profiles_profession_tag_id_tags", "user_profiles", type_="foreignkey"
    )
    op.drop_column("user_profiles", "profession_tag_id")
