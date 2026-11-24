"""init schema

Revision ID: 0001
Revises:
Create Date: 2026-11-21

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # справочные таблицы тегов
    op.create_table(
        "tag_groups",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name_ru", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tag_groups")),
        sa.UniqueConstraint("code", name=op.f("uq_tag_groups_code")),
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "group_id",
            sa.BigInteger(),
            sa.ForeignKey("tag_groups.id", ondelete="RESTRICT", name=op.f("fk_tags_group_id_tag_groups")),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            sa.BigInteger(),
            sa.ForeignKey("tags.id", ondelete="RESTRICT", name=op.f("fk_tags_parent_id_tags")),
            nullable=True,
        ),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name_ru", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tags")),
        sa.UniqueConstraint("group_id", "slug", name=op.f("uq_tags_group_id")),
    )
    op.create_index(op.f("ix_tags_parent_id"), "tags", ["parent_id"])

    # пользователи и сессии
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("google_sub", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column(
            "role",
            sa.Enum("user", "moderator", "editor", "admin", name="user_role"),
            server_default="user",
            nullable=False,
        ),
        sa.Column("is_private", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("onboarding_completed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("google_sub", name=op.f("uq_users_google_sub")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name=op.f("fk_sessions_user_id_users")),
            nullable=False,
        ),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
    )
    op.create_index(op.f("ix_sessions_expires_at"), "sessions", ["expires_at"])
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"])

    op.create_table(
        "user_profiles",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name=op.f("fk_user_profiles_user_id_users")),
            nullable=False,
        ),
        sa.Column(
            "age_tag_id",
            sa.BigInteger(),
            sa.ForeignKey("tags.id", ondelete="RESTRICT", name=op.f("fk_user_profiles_age_tag_id_tags")),
            nullable=True,
        ),
        sa.Column(
            "country_tag_id",
            sa.BigInteger(),
            sa.ForeignKey("tags.id", ondelete="RESTRICT", name=op.f("fk_user_profiles_country_tag_id_tags")),
            nullable=True,
        ),
        sa.Column(
            "current_field_tag_id",
            sa.BigInteger(),
            sa.ForeignKey("tags.id", ondelete="RESTRICT", name=op.f("fk_user_profiles_current_field_tag_id_tags")),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_user_profiles")),
    )
    op.create_index(op.f("ix_user_profiles_age_tag_id"), "user_profiles", ["age_tag_id"])
    op.create_index(op.f("ix_user_profiles_country_tag_id"), "user_profiles", ["country_tag_id"])
    op.create_index(op.f("ix_user_profiles_current_field_tag_id"), "user_profiles", ["current_field_tag_id"])

    op.create_table(
        "user_selected_tags",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name=op.f("fk_user_selected_tags_user_id_users")),
            nullable=False,
        ),
        sa.Column(
            "tag_id",
            sa.BigInteger(),
            sa.ForeignKey("tags.id", ondelete="RESTRICT", name=op.f("fk_user_selected_tags_tag_id_tags")),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "tag_id", name=op.f("pk_user_selected_tags")),
    )

    # истории
    op.create_table(
        "stories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("woman_name", sa.String(length=150), nullable=False),
        sa.Column("short_description", sa.String(length=500), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column(
            "story_type",
            sa.Enum("verified_biography", "community_story", name="story_type"),
            nullable=False,
        ),
        sa.Column(
            "verification_status",
            sa.Enum("pending", "verified", "rejected", "needs_revision", name="verification_status"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "publication_status",
            sa.Enum("draft", "published", "archived", name="publication_status"),
            server_default="draft",
            nullable=False,
        ),
        sa.Column(
            "country_tag_id",
            sa.BigInteger(),
            sa.ForeignKey("tags.id", ondelete="RESTRICT", name=op.f("fk_stories_country_tag_id_tags")),
            nullable=True,
        ),
        sa.Column(
            "profession_tag_id",
            sa.BigInteger(),
            sa.ForeignKey("tags.id", ondelete="RESTRICT", name=op.f("fk_stories_profession_tag_id_tags")),
            nullable=True,
        ),
        sa.Column(
            "age_tag_id",
            sa.BigInteger(),
            sa.ForeignKey("tags.id", ondelete="RESTRICT", name=op.f("fk_stories_age_tag_id_tags")),
            nullable=True,
        ),
        sa.Column("is_anonymous", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name=op.f("fk_stories_created_by_users")),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stories")),
        sa.UniqueConstraint("slug", name=op.f("uq_stories_slug")),
    )
    op.create_index(op.f("ix_stories_age_tag_id"), "stories", ["age_tag_id"])
    op.create_index(op.f("ix_stories_country_tag_id"), "stories", ["country_tag_id"])
    op.create_index(op.f("ix_stories_profession_tag_id"), "stories", ["profession_tag_id"])
    op.create_index("ix_stories_publication_status", "stories", ["publication_status"])

    op.create_table(
        "story_tags",
        sa.Column(
            "story_id",
            sa.Uuid(),
            sa.ForeignKey("stories.id", ondelete="CASCADE", name=op.f("fk_story_tags_story_id_stories")),
            nullable=False,
        ),
        sa.Column(
            "tag_id",
            sa.BigInteger(),
            sa.ForeignKey("tags.id", ondelete="RESTRICT", name=op.f("fk_story_tags_tag_id_tags")),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("story_id", "tag_id", name=op.f("pk_story_tags")),
    )
    op.create_index("ix_story_tags_tag_id", "story_tags", ["tag_id"])

    op.create_table(
        "story_sources",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "story_id",
            sa.Uuid(),
            sa.ForeignKey("stories.id", ondelete="CASCADE", name=op.f("fk_story_sources_story_id_stories")),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column(
            "source_type",
            sa.Enum("book", "article", "interview", "document", "video", "archive", "other", name="source_type"),
            server_default="other",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_story_sources")),
    )
    op.create_index(op.f("ix_story_sources_story_id"), "story_sources", ["story_id"])

    op.create_table(
        "favorites",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name=op.f("fk_favorites_user_id_users")),
            nullable=False,
        ),
        sa.Column(
            "story_id",
            sa.Uuid(),
            sa.ForeignKey("stories.id", ondelete="CASCADE", name=op.f("fk_favorites_story_id_stories")),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "story_id", name=op.f("pk_favorites")),
    )
    op.create_index("ix_favorites_story_id", "favorites", ["story_id"])


def downgrade() -> None:
    op.drop_table("favorites")
    op.drop_table("story_sources")
    op.drop_table("story_tags")
    op.drop_index("ix_stories_publication_status", table_name="stories")
    op.drop_index(op.f("ix_stories_profession_tag_id"), table_name="stories")
    op.drop_index(op.f("ix_stories_country_tag_id"), table_name="stories")
    op.drop_index(op.f("ix_stories_age_tag_id"), table_name="stories")
    op.drop_table("stories")
    op.drop_table("user_selected_tags")
    op.drop_index(op.f("ix_user_profiles_current_field_tag_id"), table_name="user_profiles")
    op.drop_index(op.f("ix_user_profiles_country_tag_id"), table_name="user_profiles")
    op.drop_index(op.f("ix_user_profiles_age_tag_id"), table_name="user_profiles")
    op.drop_table("user_profiles")
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_expires_at"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("users")
    op.drop_index(op.f("ix_tags_parent_id"), table_name="tags")
    op.drop_table("tags")
    op.drop_table("tag_groups")
    # типы enum остаются в бд, postgres не умеет drop type if exists в alembic штатно
    for enum_name in (
        "user_role",
        "story_type",
        "verification_status",
        "publication_status",
        "source_type",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
