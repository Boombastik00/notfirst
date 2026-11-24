import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import UserRole


def user_role_enum() -> sa.Enum:
    # храним значения enum а не имена
    return sa.Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e])


class User(Base):
    # якорь аккаунта: только роли и флаги, данные входа в auth_identities
    # а всё что пользовательница рассказала о себе в user_profiles
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(), primary_key=True, default=uuid.uuid4)
    role: Mapped[UserRole] = mapped_column(user_role_enum(), server_default="user")
    is_private: Mapped[bool] = mapped_column(server_default=sa.true())
    onboarding_completed: Mapped[bool] = mapped_column(server_default=sa.false())
    # одноразовое уведомление: историю авторки отклонили на модерации
    has_rejection_notice: Mapped[bool] = mapped_column(server_default=sa.false())
    # бан: вход запрещён, сессии отозваны
    is_banned: Mapped[bool] = mapped_column(server_default=sa.false())
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class AuthIdentity(Base):
    # способ входа: одна пользовательница может иметь несколько записей
    # например google сейчас и другие провайдеры позже
    __tablename__ = "auth_identities"
    __table_args__ = (sa.UniqueConstraint("provider", "provider_sub"),)

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(sa.String(50))
    provider_sub: Mapped[str] = mapped_column(sa.String(255))
    email: Mapped[str] = mapped_column(sa.String(320))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class UserSession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(), primary_key=True, default=uuid.uuid4)
    token_hash: Mapped[str] = mapped_column(sa.String(64), unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    user_agent: Mapped[str | None] = mapped_column(sa.String(300))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class UserConsent(Base):
    # журнал согласий: фиксируем что и в какой редакции пользовательница приняла
    __tablename__ = "user_consents"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(sa.String(50))
    version: Mapped[str] = mapped_column(sa.String(20))
    note: Mapped[str | None] = mapped_column(sa.String(200))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )


class UserBadge(Base):
    # префикс на профиле: виден всем, выдаёт персонал
    __tablename__ = "user_badges"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    badge: Mapped[str] = mapped_column(sa.String(30))
    granted_by: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid())
    granted_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str | None] = mapped_column(sa.String(100))
    avatar_url: Mapped[str | None] = mapped_column(sa.String(500))
    # короткий текст о себе на будущее, для профиля коммьюнити
    bio: Mapped[str | None] = mapped_column(sa.Text)
    age_tag_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("tags.id", ondelete="RESTRICT"), index=True
    )
    country_tag_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("tags.id", ondelete="RESTRICT"), index=True
    )
    profession_tag_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("tags.id", ondelete="RESTRICT"), index=True
    )
    current_field_tag_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("tags.id", ondelete="RESTRICT"), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class UserSelectedTag(Base):
    __tablename__ = "user_selected_tags"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        sa.ForeignKey("tags.id", ondelete="RESTRICT"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
