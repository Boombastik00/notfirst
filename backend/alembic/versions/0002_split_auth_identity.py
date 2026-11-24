"""split auth identity from user account

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-21

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_identities",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name=op.f("fk_auth_identities_user_id_users")),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_sub", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_identities")),
        sa.UniqueConstraint("provider", "provider_sub", name=op.f("uq_auth_identities_provider")),
    )
    op.create_index(op.f("ix_auth_identities_user_id"), "auth_identities", ["user_id"])

    # переносим существующие google-входы в новую таблицу
    op.execute(
        "INSERT INTO auth_identities (user_id, provider, provider_sub, email, created_at, updated_at) "
        "SELECT id, 'google', google_sub, email, created_at, updated_at FROM users"
    )

    # имя и аватар переезжают в профиль
    op.add_column("user_profiles", sa.Column("display_name", sa.String(length=100), nullable=True))
    op.add_column("user_profiles", sa.Column("avatar_url", sa.String(length=500), nullable=True))
    op.execute(
        "UPDATE user_profiles p SET display_name = u.display_name, avatar_url = u.avatar_url "
        "FROM users u WHERE p.user_id = u.id"
    )

    op.drop_constraint("uq_users_google_sub", "users", type_="unique")
    op.drop_column("users", "google_sub")
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_column("users", "email")
    op.drop_column("users", "display_name")
    op.drop_column("users", "avatar_url")


def downgrade() -> None:
    # обратный перенос лучшее что возможно: первый google-вход каждого аккаунта
    op.add_column("users", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("email", sa.String(length=320), nullable=True))
    op.add_column("users", sa.Column("display_name", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))
    op.execute(
        "UPDATE users u SET google_sub = i.provider_sub, email = i.email "
        "FROM (SELECT DISTINCT ON (user_id) * FROM auth_identities WHERE provider = 'google' "
        "ORDER BY user_id, id) i WHERE u.id = i.user_id"
    )
    op.execute(
        "UPDATE users u SET display_name = p.display_name, avatar_url = p.avatar_url "
        "FROM user_profiles p WHERE u.id = p.user_id"
    )
    op.create_unique_constraint("uq_users_google_sub", "users", ["google_sub"])
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.drop_column("user_profiles", "avatar_url")
    op.drop_column("user_profiles", "display_name")

    op.drop_index(op.f("ix_auth_identities_user_id"), table_name="auth_identities")
    op.drop_table("auth_identities")
