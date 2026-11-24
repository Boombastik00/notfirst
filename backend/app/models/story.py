import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import PublicationStatus, SourceType, StoryType, VerificationStatus


def story_type_enum() -> sa.Enum:
    return sa.Enum(
        StoryType, name="story_type", values_callable=lambda e: [m.value for m in e]
    )


def verification_status_enum() -> sa.Enum:
    return sa.Enum(
        VerificationStatus,
        name="verification_status",
        values_callable=lambda e: [m.value for m in e],
    )


def publication_status_enum() -> sa.Enum:
    return sa.Enum(
        PublicationStatus,
        name="publication_status",
        values_callable=lambda e: [m.value for m in e],
    )


def source_type_enum() -> sa.Enum:
    return sa.Enum(
        SourceType, name="source_type", values_callable=lambda e: [m.value for m in e]
    )


class Story(Base):
    __tablename__ = "stories"
    __table_args__ = (sa.Index("ix_stories_publication_status", "publication_status"),)

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(sa.String(120), unique=True)
    title: Mapped[str] = mapped_column(sa.String(200))
    woman_name: Mapped[str] = mapped_column(sa.String(150))
    short_description: Mapped[str] = mapped_column(sa.String(500))
    full_text: Mapped[str] = mapped_column(sa.Text)
    story_type: Mapped[StoryType] = mapped_column(story_type_enum())
    verification_status: Mapped[VerificationStatus] = mapped_column(
        verification_status_enum(), server_default="pending"
    )
    publication_status: Mapped[PublicationStatus] = mapped_column(
        publication_status_enum(), server_default="draft"
    )
    country_tag_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("tags.id", ondelete="RESTRICT"), index=True
    )
    profession_tag_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("tags.id", ondelete="RESTRICT"), index=True
    )
    age_tag_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("tags.id", ondelete="RESTRICT"), index=True
    )
    is_anonymous: Mapped[bool] = mapped_column(server_default=sa.false())
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class StoryTag(Base):
    __tablename__ = "story_tags"

    story_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        sa.ForeignKey("tags.id", ondelete="RESTRICT"), primary_key=True
    )


sa.Index("ix_story_tags_tag_id", StoryTag.tag_id)


class StorySource(Base):
    __tablename__ = "story_sources"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    story_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("stories.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(sa.String(300))
    url: Mapped[str | None] = mapped_column(sa.String(1000))
    source_type: Mapped[SourceType] = mapped_column(source_type_enum(), server_default="other")
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
