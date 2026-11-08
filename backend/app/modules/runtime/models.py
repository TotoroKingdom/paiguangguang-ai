from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models import uuid_string


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (Index("ix_agent_runs_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    capability_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    version_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="fake")
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="fake")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    input_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    output_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error_code: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    error_message: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    token_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    step_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    steps: Mapped[list["RunStep"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="RunStep.seq"
    )
    traces: Mapped[list["RunTrace"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="RunTrace.seq"
    )


class RunStep(Base):
    __tablename__ = "run_steps"
    __table_args__ = (Index("ix_run_steps_run_seq", "run_id", "seq"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="running")
    input_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    output_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    error: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    run: Mapped[AgentRun] = relationship(back_populates="steps")


class RunTrace(Base):
    __tablename__ = "run_traces"
    __table_args__ = (Index("ix_run_traces_run_seq", "run_id", "seq"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    event: Mapped[str] = mapped_column(String(48), nullable=False)
    detail_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    run: Mapped[AgentRun] = relationship(back_populates="traces")
