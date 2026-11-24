from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TagGroup(Base):
    __tablename__ = "tag_groups"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(sa.String(50), unique=True)
    name_ru: Mapped[str] = mapped_column(sa.String(100))
    sort_order: Mapped[int] = mapped_column(server_default="0")
    is_system: Mapped[bool] = mapped_column(server_default=sa.false())


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (sa.UniqueConstraint("group_id", "slug"),)

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(sa.ForeignKey("tag_groups.id", ondelete="RESTRICT"))
    parent_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("tags.id", ondelete="RESTRICT"), index=True
    )
    slug: Mapped[str] = mapped_column(sa.String(80))
    name_ru: Mapped[str] = mapped_column(sa.String(150))
    description: Mapped[str | None] = mapped_column(sa.String(500))
    is_active: Mapped[bool] = mapped_column(server_default=sa.true())
    sort_order: Mapped[int] = mapped_column(server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )

    group: Mapped[TagGroup] = relationship()

    @property
    def group_code(self) -> str:
        return self.group.code
