from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models import uuid_string


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sessions: Mapped[list["AdminSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AdminSession(Base):
    __tablename__ = "admin_sessions"
    __table_args__ = (
        Index("ix_admin_sessions_token_hash", "token_hash", unique=True),
        Index("ix_admin_sessions_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    csrf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    client_ip: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    user_agent: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    user: Mapped[AdminUser] = relationship(back_populates="sessions")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("account_number", name="uq_users_account_number"),
        Index("ix_users_status_role", "status", "role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    account_number: Mapped[str] = mapped_column(String(32), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="USER")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    status_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    authz_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AccountSequence(Base):
    __tablename__ = "account_sequences"

    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    next_account_number: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegistrationIdempotency(Base):
    __tablename__ = "registration_idempotency"
    __table_args__ = (Index("ix_registration_idempotency_created_at", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    response_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_token_hash", "token_hash", unique=True),
        Index("ix_user_sessions_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    csrf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="FULL")
    authz_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_ip: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    user_agent: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    user: Mapped[User] = relationship(back_populates="sessions")


class UserRecoveryCode(Base):
    __tablename__ = "user_recovery_codes"
    __table_args__ = (Index("ix_user_recovery_codes_user", "user_id", "used_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminUserLink(Base):
    __tablename__ = "admin_user_links"
    __table_args__ = (
        UniqueConstraint("legacy_admin_id", name="uq_admin_user_links_legacy"),
        UniqueConstraint("user_id", name="uq_admin_user_links_user"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    legacy_admin_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    migrated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    migration_source: Mapped[str] = mapped_column(String(48), nullable=False, default="bootstrap")


class AuthRateEvent(Base):
    __tablename__ = "auth_rate_events"
    __table_args__ = (
        Index("ix_auth_rate_events_bucket", "action", "bucket", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
