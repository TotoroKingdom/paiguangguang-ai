from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models import uuid_string


class PersonalSkill(Base):
    __tablename__ = "personal_skills"
    __table_args__ = (Index("ix_personal_skills_user_updated", "user_id", "updated_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserFile(Base):
    __tablename__ = "user_files"
    __table_args__ = (Index("ix_user_files_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False, default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class McpServer(Base):
    __tablename__ = "mcp_servers"
    __table_args__ = (UniqueConstraint("name", name="uq_mcp_servers_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    endpoint_url: Mapped[str] = mapped_column(String(512), nullable=False)
    transport: Mapped[str] = mapped_column(String(16), nullable=False, default="http")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    tools_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    tool_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tools: Mapped[list["McpServerTool"]] = relationship(
        back_populates="server", cascade="all, delete-orphan", order_by="McpServerTool.name"
    )


class McpServerTool(Base):
    """Persisted server-side approval boundary for one MCP tool.

    The remote server's annotations are discovery hints only. Runtime policy
    consumes this row's approval and risk fields, which are written by an
    administrator and invalidated whenever the discovered schema changes.
    """

    __tablename__ = "mcp_server_tools"
    __table_args__ = (
        UniqueConstraint("server_id", "name", name="uq_mcp_server_tools_server_name"),
        Index("ix_mcp_server_tools_server_status", "server_id", "approval_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    server_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    input_schema_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    output_schema_json: Mapped[str] = mapped_column(Text, nullable=False, default="null")
    schema_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    approval_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    risk_class: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    approval_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    approved_by: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    server: Mapped[McpServer] = relationship(back_populates="tools")


class McpConnection(Base):
    __tablename__ = "mcp_connections"
    __table_args__ = (
        UniqueConstraint("user_id", "server_id", name="uq_mcp_connections_user_server"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    server_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="connected")
    credential_ciphertext: Mapped[str] = mapped_column(Text, nullable=False, default="")
    credential_ref: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
