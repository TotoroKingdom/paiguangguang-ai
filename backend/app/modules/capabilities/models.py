from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models import uuid_string


class CapabilityDefinition(Base):
    __tablename__ = "capability_definitions"
    __table_args__ = (
        UniqueConstraint("kind", "slug", name="uq_capability_definitions_kind_slug"),
        Index("ix_capability_definitions_kind_status", "kind", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="未分类")
    icon: Mapped[str] = mapped_column(String(48), nullable=False, default="spark")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="admin")
    created_by: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, default="platform")
    access_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="all_active")
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    submitted_by: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    test_status: Mapped[str] = mapped_column(String(16), nullable=False, default="untested")
    tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    test_detail_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    versions: Mapped[list["CapabilityVersion"]] = relationship(
        back_populates="capability",
        cascade="all, delete-orphan",
        order_by="CapabilityVersion.version",
    )


class CapabilityVersion(Base):
    __tablename__ = "capability_versions"
    __table_args__ = (
        UniqueConstraint("capability_id", "version", name="uq_capability_versions_number"),
        Index("ix_capability_versions_status", "capability_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    capability_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("capability_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    changelog: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    published_by: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    capability: Mapped[CapabilityDefinition] = relationship(back_populates="versions")
    dependencies: Mapped[list["CapabilityDependency"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class CapabilityDependency(Base):
    __tablename__ = "capability_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "version_id", "dependency_id", name="uq_capability_dependencies_version_target"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("capability_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dependency_id: Mapped[str] = mapped_column(String(36), nullable=False)
    dependency_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    dependency_version_id: Mapped[str] = mapped_column(
        String(36), nullable=False, default=""
    )
    version: Mapped[CapabilityVersion] = relationship(back_populates="dependencies")


class CapabilityRun(Base):
    __tablename__ = "capability_runs"
    __table_args__ = (Index("ix_capability_runs_created_at", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    capability_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="demo")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="accepted")
    detail_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CapabilityGrant(Base):
    __tablename__ = "capability_grants"
    __table_args__ = (
        UniqueConstraint("capability_id", "user_id", name="uq_capability_grants_target"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    capability_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("capability_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    granted_by: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CapabilityReview(Base):
    __tablename__ = "capability_reviews"
    __table_args__ = (Index("ix_capability_reviews_capability", "capability_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    capability_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
