from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
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
