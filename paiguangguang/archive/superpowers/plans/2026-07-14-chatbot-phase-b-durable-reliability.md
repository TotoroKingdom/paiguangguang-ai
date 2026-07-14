# Chatbot Phase B Durable Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复缺陷 4–7，以 PostgreSQL durable job 连接同步/流式完成链路，启动可靠恢复和清理补偿，并让 Redis 运行期故障可降级。

**Architecture:** `chatbot_jobs` 是提交后工作的持久 outbox。消息完成或资源软删除时在同一数据库事务入队，应用 lifespan 的单一 worker 周期认领任务；Redis/Chroma 只在 worker 或可降级适配器中访问，不能决定消息和删除事务是否成功。

**Tech Stack:** Python 3.12、FastAPI lifespan、SQLAlchemy 2、Alembic、PostgreSQL/SQLite tests、Redis 5、ChromaDB、pytest。

## Global Constraints

- PostgreSQL 是唯一业务事实源；Redis 和 Chroma 可清空、可失败、可重建。
- 外部 LLM、Redis、Chroma 调用不得发生在消息终态或删除主事务中。
- durable job dedup key 必须稳定且有数据库唯一约束。
- SSE replay 不得重新入队；失败/cancelled turn 不提取长期记忆或自动标题。
- 删除接口在 PostgreSQL commit 后即向用户返回成功；外部清理失败进入 retry。
- Redis lease 永远不是唯一并发保障；Conversation 行锁和 active-run 查询保持不变。
- 所有日志脱敏，不保存正文、JWT、Provider key 或完整 Redis URL。

---

## File Map

- Create: `backend/app/chatbot/models/job.py` — durable job ORM。
- Create: `backend/alembic/versions/0007_create_chatbot_jobs.py` — job 表、约束和索引。
- Modify: `backend/app/chatbot/models/__init__.py` — 注册 job model。
- Create: `backend/app/chatbot/repositories/job_repository.py` — enqueue/claim/complete/retry/recover。
- Create: `backend/tests/chatbot/test_job_repository.py` — durable job repository 测试。
- Create: `backend/app/chatbot/services/completion_jobs.py` — completed turn 入队和 auto title CAS。
- Modify: `backend/app/chatbot/services/chat_service.py` — 同步完成事务入队，删除内存 queue 调用。
- Modify: `backend/app/chatbot/services/stream_service.py` — 流式完成事务入队，terminal SSE 前不做摘要。
- Create: `backend/app/chatbot/services/job_runner.py` — job handler 分派和重试。
- Create: `backend/app/chatbot/services/runtime.py` — lifespan worker。
- Modify: `backend/app/chatbot/services/recovery_service.py` — stale run compare-and-set。
- Modify: `backend/app/main.py` — start/stop runtime。
- Create: `backend/app/chatbot/services/cleanup_service.py` — Redis/Chroma cleanup handler。
- Modify: `backend/app/chatbot/services/conversation_service.py` — 会话删除事务软删 memories 并入队。
- Modify: `backend/app/chatbot/services/memory_service.py` — Memory 删除事务入队。
- Modify: `backend/app/chatbot/repositories/memory_repository.py` — 排除 deleted Conversation 的 memories。
- Modify: `backend/app/chatbot/memory/short_term_memory.py` — 精确删除三类 Redis keys。
- Modify: `backend/app/chatbot/services/cancellation_service.py` — 运行期 Redis 故障降级。
- Modify: `backend/app/chatbot/services/concurrency_service.py` — 运行期 Redis 故障降级。
- Modify: `backend/app/core/config.py`、`backend/.env.example` — job/recovery 配置。
- Create: `backend/tests/chatbot/test_completion_jobs.py`、`test_chatbot_runtime.py`、`test_cleanup_retry.py`、`test_redis_degradation.py`。

### Task 1: 建立 durable job 数据模型和 repository

**Files:**
- Create: `backend/app/chatbot/models/job.py`
- Modify: `backend/app/chatbot/models/__init__.py`
- Create: `backend/alembic/versions/0007_create_chatbot_jobs.py`
- Create: `backend/app/chatbot/repositories/job_repository.py`
- Create: `backend/tests/chatbot/test_job_repository.py`

**Interfaces:**
- Produces: `ChatbotJob`。
- Produces: `JobRepository.enqueue(session, *, kind, dedup_key, payload)`。
- Produces: `claim_batch(limit) -> list[JobRecord]`、`mark_completed(job_id)`、`mark_retry(job_id, error, delay_seconds, max_attempts)`、`recover_stale(stale_seconds)`。

- [ ] **Step 1: 写 job repository 失败测试**

创建 `backend/tests/chatbot/test_job_repository.py`，复用现有 SQLite `Base.metadata.create_all` 模式：

```python
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.job import ChatbotJob
from app.chatbot.repositories.job_repository import JobRepository
from app.db.base import Base


def _factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite+pysqlite:///{(tmp_path / f'{uuid4()}.sqlite3').as_posix()}",
        future=True,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def test_job_repository_deduplicates_claims_and_completes(tmp_path) -> None:
    factory = _factory(tmp_path)
    repository = JobRepository(factory)
    with factory() as session:
        first = repository.enqueue(
            session,
            kind="completed_turn_memory",
            dedup_key="memory:user-message-1",
            payload={"user_message_id": "user-message-1"},
        )
        second = repository.enqueue(
            session,
            kind="completed_turn_memory",
            dedup_key="memory:user-message-1",
            payload={"user_message_id": "user-message-1"},
        )
        session.commit()

    assert first.id == second.id
    claimed = repository.claim_batch(limit=10)
    assert [item.id for item in claimed] == [first.id]
    assert claimed[0].status == "running"
    assert claimed[0].attempt_count == 1

    repository.mark_completed(first.id)
    with factory() as session:
        row = session.scalar(select(ChatbotJob).where(ChatbotJob.id == first.id))
    assert row is not None
    assert row.status == "completed"
    assert repository.claim_batch(limit=10) == []


def test_job_repository_retries_then_fails_at_max_attempts(tmp_path) -> None:
    factory = _factory(tmp_path)
    repository = JobRepository(factory)
    with factory() as session:
        job = repository.enqueue(
            session,
            kind="cleanup_memory",
            dedup_key="cleanup-memory:1",
            payload={"memory_id": "1"},
        )
        session.commit()

    repository.claim_batch(limit=1)
    repository.mark_retry(job.id, error="RuntimeError: unavailable", delay_seconds=0, max_attempts=2)
    assert repository.claim_batch(limit=1)[0].attempt_count == 2
    repository.mark_retry(job.id, error="RuntimeError: unavailable", delay_seconds=0, max_attempts=2)

    with factory() as session:
        row = session.get(ChatbotJob, job.id)
    assert row is not None
    assert row.status == "failed"
```

- [ ] **Step 2: 运行测试，确认 model/repository 尚不存在**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_job_repository.py -q
```

Expected: collection ERROR，`app.chatbot.models.job` 不存在。

- [ ] **Step 3: 创建 `ChatbotJob` model**

创建 `backend/app/chatbot/models/job.py`：

```python
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, JSON, String, UniqueConstraint, text as sa_text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatbotJob(Base):
    __tablename__ = "chatbot_jobs"
    __table_args__ = (
        UniqueConstraint("dedup_key", name="uq_chatbot_jobs_dedup_key"),
        CheckConstraint(
            "kind IN ('completed_turn_memory', 'refresh_conversation_context', "
            "'auto_title', 'cleanup_conversation', 'cleanup_memory')",
            name="ck_chatbot_jobs_kind",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'retry', 'completed', 'failed')",
            name="ck_chatbot_jobs_status",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_chatbot_jobs_attempt_count"),
        Index("ix_chatbot_jobs_status_available_at_id", "status", "available_at", "id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=sa_text("0"))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
```

在 `models/__init__.py` 导入并加入 `__all__`：

```python
from app.chatbot.models.job import ChatbotJob
```

- [ ] **Step 4: 创建 Alembic 0007 migration**

创建 `backend/alembic/versions/0007_create_chatbot_jobs.py`，字段与 model 完全一致：

```python
"""create chatbot durable jobs

Revision ID: 0007_create_chatbot_jobs
Revises: 0006_create_chatbot_tables
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_create_chatbot_jobs"
down_revision = "0006_create_chatbot_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chatbot_jobs",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("dedup_key", sa.String(255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("dedup_key", name="uq_chatbot_jobs_dedup_key"),
        sa.CheckConstraint(
            "kind IN ('completed_turn_memory', 'refresh_conversation_context', 'auto_title', "
            "'cleanup_conversation', 'cleanup_memory')",
            name="ck_chatbot_jobs_kind",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'retry', 'completed', 'failed')",
            name="ck_chatbot_jobs_status",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_chatbot_jobs_attempt_count"),
    )
    op.create_index(
        "ix_chatbot_jobs_status_available_at_id",
        "chatbot_jobs",
        ["status", "available_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_chatbot_jobs_status_available_at_id", table_name="chatbot_jobs")
    op.drop_table("chatbot_jobs")
```

- [ ] **Step 5: 实现 `JobRepository`**

创建 `backend/app/chatbot/repositories/job_repository.py`，实现以下完整公开行为；`enqueue` 使用 nested transaction 处理并发唯一键，不能 rollback 外层消息事务：

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.job import ChatbotJob


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class JobRecord:
    id: str
    kind: str
    dedup_key: str
    payload: dict[str, object]
    status: str
    attempt_count: int


class JobRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    @staticmethod
    def _record(row: ChatbotJob) -> JobRecord:
        return JobRecord(
            id=row.id,
            kind=row.kind,
            dedup_key=row.dedup_key,
            payload=dict(row.payload or {}),
            status=row.status,
            attempt_count=row.attempt_count,
        )

    def enqueue(
        self,
        session: Session,
        *,
        kind: str,
        dedup_key: str,
        payload: dict[str, object],
    ) -> ChatbotJob:
        existing = session.scalar(select(ChatbotJob).where(ChatbotJob.dedup_key == dedup_key))
        if existing is not None:
            return existing
        row = ChatbotJob(kind=kind, dedup_key=dedup_key, payload=dict(payload), status="pending")
        try:
            with session.begin_nested():
                session.add(row)
                session.flush()
        except IntegrityError:
            winner = session.scalar(select(ChatbotJob).where(ChatbotJob.dedup_key == dedup_key))
            if winner is None:
                raise
            return winner
        return row

    def claim_batch(self, *, limit: int = 20) -> list[JobRecord]:
        if limit < 1:
            raise ValueError("limit must be positive")
        now = _utcnow()
        with self.session_factory() as session:
            rows = list(
                session.scalars(
                    select(ChatbotJob)
                    .where(
                        ChatbotJob.status.in_(("pending", "retry")),
                        ChatbotJob.available_at <= now,
                    )
                    .order_by(ChatbotJob.available_at.asc(), ChatbotJob.id.asc())
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            )
            for row in rows:
                row.status = "running"
                row.attempt_count += 1
                row.locked_at = now
                row.updated_at = now
            session.commit()
            return [self._record(row) for row in rows]

    def mark_completed(self, job_id: str) -> None:
        now = _utcnow()
        with self.session_factory() as session:
            session.execute(
                update(ChatbotJob)
                .where(ChatbotJob.id == job_id, ChatbotJob.status == "running")
                .values(status="completed", completed_at=now, locked_at=None, last_error=None, updated_at=now)
            )
            session.commit()

    def mark_retry(
        self,
        job_id: str,
        *,
        error: str,
        delay_seconds: int,
        max_attempts: int,
    ) -> None:
        now = _utcnow()
        with self.session_factory() as session:
            row = session.get(ChatbotJob, job_id)
            if row is None or row.status != "running":
                return
            row.status = "failed" if row.attempt_count >= max_attempts else "retry"
            row.available_at = now + timedelta(seconds=max(0, delay_seconds))
            row.locked_at = None
            row.last_error = error[:500]
            row.updated_at = now
            session.commit()

    def recover_stale(self, *, stale_seconds: int) -> int:
        now = _utcnow()
        cutoff = now - timedelta(seconds=max(1, stale_seconds))
        with self.session_factory() as session:
            result = session.execute(
                update(ChatbotJob)
                .where(ChatbotJob.status == "running", ChatbotJob.locked_at < cutoff)
                .values(status="retry", available_at=now, locked_at=None, updated_at=now)
            )
            session.commit()
            return int(result.rowcount or 0)
```

- [ ] **Step 6: 运行 repository 和 migration 测试**

创建 `backend/tests/chatbot/test_migration_0007.py`：

```python
from __future__ import annotations

import sqlite3
from alembic import command
from app.db.alembic import get_alembic_config


def _configure(monkeypatch, tmp_path) -> str:
    path = tmp_path / "chatbot-migration-0007.sqlite3"
    url = f"sqlite+pysqlite:///{path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("TEST_DATABASE_URL", url)
    return path.as_posix()


def test_migration_0007_creates_durable_jobs(monkeypatch, tmp_path) -> None:
    path = _configure(monkeypatch, tmp_path)
    command.upgrade(get_alembic_config(), "head")
    with sqlite3.connect(path) as connection:
        table = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='chatbot_jobs'"
        ).fetchone()
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    assert table is not None
    assert "uq_chatbot_jobs_dedup_key" in table[0]
    assert "ck_chatbot_jobs_status" in table[0]
    assert version == ("0007_create_chatbot_jobs",)


def test_migration_0007_downgrades_to_0006(monkeypatch, tmp_path) -> None:
    path = _configure(monkeypatch, tmp_path)
    command.upgrade(get_alembic_config(), "head")
    command.downgrade(get_alembic_config(), "0006_create_chatbot_tables")
    with sqlite3.connect(path) as connection:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chatbot_jobs'"
        ).fetchone()
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    assert table is None
    assert version == ("0006_create_chatbot_tables",)
```

然后运行：

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_job_repository.py backend/tests/chatbot/test_migration_0007.py -q
```

Expected: PASS。

- [ ] **Step 7: 提交 Task 1**

```powershell
git add backend/app/chatbot/models backend/app/chatbot/repositories/job_repository.py backend/alembic/versions/0007_create_chatbot_jobs.py backend/tests/chatbot/test_job_repository.py backend/tests/chatbot/test_migration_0007.py
git commit -m "feat(chatbot): add durable job outbox"
```

### Task 2: 让同步和流式完成事务统一入队

**Files:**
- Create: `backend/app/chatbot/services/completion_jobs.py`
- Modify: `backend/app/chatbot/services/chat_service.py`
- Modify: `backend/app/chatbot/services/stream_service.py`
- Create: `backend/tests/chatbot/test_completion_jobs.py`
- Modify: `backend/tests/chatbot/test_chat_stream.py`

**Interfaces:**
- Produces: `CompletionJobService.enqueue_completed_turn(session, *, user_id, conversation_id, user_message_id, assistant_message_id)`。
- Produces: `ConversationTitleService.apply_auto_title(payload)`，仅 CAS `title_source='default'`。
- Consumes: Task 1 的 `JobRepository.enqueue`。

- [ ] **Step 1: 写 completed turn 入队和去重失败测试**

创建 `test_completion_jobs.py`，建立 user/conversation/messages 后调用两次 service：

```python
def test_completion_jobs_are_deduplicated(tmp_path) -> None:
    factory, owner_id, conversation_id, user_message_id, assistant_message_id = _seed_completed_turn(tmp_path)
    service = CompletionJobService(
        JobRepository(factory),
        settings=Settings(chatbot_long_term_memory_enabled=True),
    )
    with factory() as session:
        for _ in range(2):
            service.enqueue_completed_turn(
                session,
                user_id=owner_id,
                conversation_id=conversation_id,
                user_message_id=user_message_id,
                assistant_message_id=assistant_message_id,
            )
        session.commit()

    with factory() as session:
        jobs = list(session.scalars(select(ChatbotJob).order_by(ChatbotJob.kind)))
    assert {job.kind for job in jobs} == {
        "auto_title",
        "completed_turn_memory",
        "refresh_conversation_context",
    }
    assert len(jobs) == 3
```

在现有 `test_chat_stream.py` 的成功流测试中注入 fake `CompletionJobService`，断言 `_finalize_completed` 调用一次；对 replay 再调用一次 stream，断言仍为一次。

- [ ] **Step 2: 运行测试确认 service 不存在且流式链路未入队**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_completion_jobs.py backend/tests/chatbot/test_chat_stream.py -q
```

Expected: FAIL。

- [ ] **Step 3: 创建 CompletionJobService 和标题 CAS**

创建 `completion_jobs.py`：

```python
from __future__ import annotations

import re
from typing import Mapping

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.models.conversation import ChatbotConversation
from app.chatbot.models.message import ChatbotMessage
from app.chatbot.repositories.job_repository import JobRepository
from app.core.config import Settings, get_settings


class CompletionJobService:
    def __init__(self, repository: JobRepository, *, settings: Settings | None = None) -> None:
        self.repository = repository
        self.settings = settings or get_settings()

    def enqueue_completed_turn(
        self,
        session: Session,
        *,
        user_id: str,
        conversation_id: str,
        user_message_id: str,
        assistant_message_id: str,
    ) -> None:
        payload = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
        }
        if self.settings.chatbot_long_term_memory_enabled:
            self.repository.enqueue(
                session,
                kind="completed_turn_memory",
                dedup_key=f"completed-turn-memory:{user_message_id}",
                payload=payload,
            )
        self.repository.enqueue(
            session,
            kind="refresh_conversation_context",
            dedup_key=f"refresh-conversation-context:{assistant_message_id}",
            payload=payload,
        )
        self.repository.enqueue(
            session,
            kind="auto_title",
            dedup_key=f"auto-title:{conversation_id}",
            payload=payload,
        )


class ConversationTitleService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    @staticmethod
    def derive_title(content: str) -> str:
        normalized = re.sub(r"\s+", " ", content).strip()
        return normalized[:60] or "新对话"

    def apply_auto_title(self, payload: Mapping[str, object]) -> bool:
        conversation_id = str(payload["conversation_id"])
        user_id = str(payload["user_id"])
        user_message_id = str(payload["user_message_id"])
        with self.session_factory() as session:
            message = session.scalar(
                select(ChatbotMessage).where(
                    ChatbotMessage.id == user_message_id,
                    ChatbotMessage.user_id == user_id,
                    ChatbotMessage.conversation_id == conversation_id,
                    ChatbotMessage.role == "user",
                    ChatbotMessage.status == "completed",
                )
            )
            if message is None:
                return False
            result = session.execute(
                update(ChatbotConversation)
                .where(
                    ChatbotConversation.id == conversation_id,
                    ChatbotConversation.user_id == user_id,
                    ChatbotConversation.title_source == "default",
                    ChatbotConversation.deleted_at.is_(None),
                )
                .values(title=self.derive_title(message.content), title_source="auto")
            )
            session.commit()
            return bool(result.rowcount)
```

- [ ] **Step 4: 注入 CompletionJobService 并在终态事务内调用**

给 `ChatService.__init__` 增加参数：

```python
completion_jobs: CompletionJobService | None = None,
```

初始化：

```python
self.job_repository = JobRepository(self.session_factory)
self.completion_jobs = completion_jobs or CompletionJobService(
    self.job_repository,
    settings=self.settings,
)
```

在同步 `_finalize_completed` 的 `session.flush()` 后、返回 response 前调用：

```python
self.completion_jobs.enqueue_completed_turn(
    session,
    user_id=user_id,
    conversation_id=accepted.conversation_id,
    user_message_id=accepted.user_message_id,
    assistant_message_id=accepted.assistant_message_id,
)
```

删除 `complete()` 成功后的同步调用：

```python
self.refresh_short_term_memory(user_id, conversation_id)
self.memory_service.submit_completed_turn(
    user_id,
    conversation_id,
    accepted.user_message_id,
    accepted.assistant_message_id,
    source_message_ids=[accepted.user_message_id, accepted.assistant_message_id],
)
```

在流式 `_finalize_completed` 的 `session.flush()` 后加入相同 enqueue 调用。删除 `_produce_stream_events` completed 分支中 terminal events 之前的：

```python
self._refresh_short_term_memory(user_id, accepted.conversation_id)
```

失败和取消分支可以保留 best-effort short memory 刷新；它们不得入队长期记忆或自动标题。

- [ ] **Step 5: 运行 completion/stream 测试**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_completion_jobs.py backend/tests/chatbot/test_chat_service.py backend/tests/chatbot/test_chat_stream.py -q
```

Expected: PASS；同步、流式各入队一次，replay 不增加 job。

- [ ] **Step 6: 提交 Task 2**

```powershell
git add backend/app/chatbot/services/completion_jobs.py backend/app/chatbot/services/chat_service.py backend/app/chatbot/services/stream_service.py backend/tests/chatbot/test_completion_jobs.py backend/tests/chatbot/test_chat_stream.py
git commit -m "fix(chatbot): persist post-completion work"
```

### Task 3: 启动 durable worker 和 compare-and-set recovery

**Files:**
- Create: `backend/app/chatbot/services/job_runner.py`
- Create: `backend/app/chatbot/services/runtime.py`
- Modify: `backend/app/chatbot/services/recovery_service.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Create: `backend/tests/chatbot/test_chatbot_runtime.py`
- Modify: `backend/tests/chatbot/test_stale_recovery.py`

**Interfaces:**
- Produces: `JobRunner.run_once(limit) -> int`。
- Produces: `ChatbotRuntime.start()`、`stop()`、`run_iteration()`。
- Consumes: job handlers from CompletionJobService/MemoryService/ShortTermMemory/ConversationSummary/CleanupService。

- [ ] **Step 1: 添加 runtime 生命周期和 recovery 竞态失败测试**

`test_chatbot_runtime.py` 使用 fake runner/recovery：

```python
import asyncio

from app.chatbot.services.runtime import ChatbotRuntime
from app.core.config import Settings


class FakeRecovery:
    def __init__(self) -> None:
        self.calls = 0
    def reap_stale_runs(self) -> int:
        self.calls += 1
        return 0


class FakeJobs:
    def __init__(self) -> None:
        self.recovered = 0
        self.runs = 0
    def recover_stale(self, *, stale_seconds: int) -> int:
        self.recovered += 1
        return 0
    def run_once(self, *, limit: int) -> int:
        self.runs += 1
        return 0
    def close(self) -> None:
        return None


def test_runtime_runs_startup_iteration_and_stops() -> None:
    recovery = FakeRecovery()
    jobs = FakeJobs()
    runtime = ChatbotRuntime(
        recovery_service=recovery,
        job_runner=jobs,
        settings=Settings(chatbot_worker_interval_seconds=3600),
    )

    async def scenario() -> None:
        await runtime.start()
        await asyncio.sleep(0)
        await runtime.stop()

    asyncio.run(scenario())
    assert recovery.calls >= 1
    assert jobs.recovered == 1
    assert jobs.runs >= 1
```

在 `test_stale_recovery.py` 新增测试：先让 service 查出 stale run，再用 monkeypatch/hook 把 `updated_at` 刷新，断言 CAS 后仍为 streaming。为此将 service 内更新抽成 `_mark_stale_run(session, run_id, message_id, stale_before, now) -> bool` 并直接测试该方法。

- [ ] **Step 2: 运行测试确认 runtime/config 不存在**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_chatbot_runtime.py backend/tests/chatbot/test_stale_recovery.py -q
```

Expected: FAIL。

- [ ] **Step 3: 增加 worker 配置**

给 `Settings` 增加：

```python
chatbot_worker_interval_seconds: int = 30
chatbot_job_batch_size: int = 20
chatbot_job_max_attempts: int = 8
chatbot_job_stale_seconds: int = 300
```

在 `get_settings()` 增加对应环境变量解析，并在 `backend/.env.example` 增加：

```dotenv
CHATBOT_WORKER_INTERVAL_SECONDS=30
CHATBOT_JOB_BATCH_SIZE=20
CHATBOT_JOB_MAX_ATTEMPTS=8
CHATBOT_JOB_STALE_SECONDS=300
```

- [ ] **Step 4: 实现 JobRunner**

创建 `job_runner.py`。构造函数和 stale-job 转发接口必须明确：

```python
from __future__ import annotations

from collections.abc import Callable

from app.chatbot.memory.conversation_summary import ConversationSummaryService
from app.chatbot.memory.short_term_memory import ShortTermMemoryService
from app.chatbot.repositories.job_repository import JobRepository
from app.chatbot.services.cleanup_service import CleanupService
from app.chatbot.services.completion_jobs import ConversationTitleService
from app.chatbot.services.memory_service import MemoryService
from app.core.config import Settings, get_settings


class JobRunner:
    def __init__(
        self,
        *,
        repository: JobRepository,
        memory_service: MemoryService,
        short_term_memory: ShortTermMemoryService,
        conversation_summary: ConversationSummaryService,
        title_service: ConversationTitleService,
        cleanup_service: CleanupService,
        settings: Settings | None = None,
        close_callback: Callable[[], None] | None = None,
    ) -> None:
        self.repository = repository
        self.memory_service = memory_service
        self.short_term_memory = short_term_memory
        self.conversation_summary = conversation_summary
        self.title_service = title_service
        self.cleanup_service = cleanup_service
        self.settings = settings or get_settings()
        self._close_callback = close_callback

    def recover_stale(self, *, stale_seconds: int) -> int:
        return self.repository.recover_stale(stale_seconds=stale_seconds)

    def close(self) -> None:
        if self._close_callback is not None:
            self._close_callback()
```

任务分派必须是显式映射：

```python
def run_once(self, *, limit: int) -> int:
    jobs = self.repository.claim_batch(limit=limit)
    for job in jobs:
        try:
            if job.kind == "completed_turn_memory":
                self.memory_service.process_completed_turn(
                    str(job.payload["user_id"]),
                    str(job.payload["conversation_id"]),
                    str(job.payload["user_message_id"]),
                    str(job.payload["assistant_message_id"]),
                )
            elif job.kind == "refresh_conversation_context":
                self.short_term_memory.refresh_context(
                    str(job.payload["user_id"]),
                    str(job.payload["conversation_id"]),
                )
                self.conversation_summary.maybe_generate_summary(
                    str(job.payload["user_id"]),
                    str(job.payload["conversation_id"]),
                )
            elif job.kind == "auto_title":
                self.title_service.apply_auto_title(job.payload)
            elif job.kind == "cleanup_conversation":
                self.cleanup_service.cleanup_conversation(job.payload)
            elif job.kind == "cleanup_memory":
                self.cleanup_service.cleanup_memory(job.payload)
            else:
                raise ValueError(f"Unsupported chatbot job kind: {job.kind}")
        except Exception as exc:
            if job.kind.startswith("cleanup_"):
                self.cleanup_service.mark_retry(job.payload)
            delay = min(300, 2 ** job.attempt_count)
            self.repository.mark_retry(
                job.id,
                error=f"{type(exc).__name__}: {str(exc)[:440]}",
                delay_seconds=delay,
                max_attempts=self.settings.chatbot_job_max_attempts,
            )
        else:
            self.repository.mark_completed(job.id)
    return len(jobs)
```

不要复用 `MemoryService.submit_completed_turn()` 的内存 Queue；durable worker 必须同步调用 `process_completed_turn()`，完成后才把 job 标为 completed。

- [ ] **Step 5: 实现 runtime 并挂接 FastAPI lifespan**

创建 `runtime.py`，使用 `asyncio.to_thread` 运行同步 service，停止通过 Event 而非长时间 sleep：

```python
from __future__ import annotations

import asyncio

from app.chatbot.llm.client import LLMClient
from app.chatbot.llm.deepseek_provider import DeepSeekProvider
from app.chatbot.memory.conversation_summary import ConversationSummaryService
from app.chatbot.memory.short_term_memory import ShortTermMemoryService
from app.chatbot.repositories.job_repository import JobRepository
from app.chatbot.services.cleanup_service import CleanupService
from app.chatbot.services.completion_jobs import ConversationTitleService
from app.chatbot.services.job_runner import JobRunner
from app.chatbot.services.memory_service import MemoryService
from app.chatbot.services.recovery_service import RecoveryService
from app.core.config import Settings, get_settings
from app.db.session import build_session_factory


class ChatbotRuntime:
    def __init__(self, *, recovery_service, job_runner, settings=None) -> None:
        self.settings = settings or get_settings()
        self.recovery_service = recovery_service
        self.job_runner = job_runner
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def run_iteration(self) -> None:
        await asyncio.to_thread(self.recovery_service.reap_stale_runs)
        await asyncio.to_thread(
            self.job_runner.run_once,
            limit=self.settings.chatbot_job_batch_size,
        )

    async def _loop(self) -> None:
        while not self._stop.is_set():
            await self.run_iteration()
            try:
                await asyncio.wait_for(
                    self._stop.wait(),
                    timeout=max(1, self.settings.chatbot_worker_interval_seconds),
                )
            except TimeoutError:
                continue

    async def start(self) -> None:
        await asyncio.to_thread(
            self.job_runner.recover_stale,
            stale_seconds=self.settings.chatbot_job_stale_seconds,
        )
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(), name="chatbot-runtime")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None
        await asyncio.to_thread(self.job_runner.close)
```

提供 `build_chatbot_runtime()`，每个 FastAPI lifespan 创建一个 runtime，并使用同一个 `session_factory` 组装依赖；不要缓存已被 stop/close 的 singleton：

```python
def build_chatbot_runtime(settings: Settings | None = None) -> ChatbotRuntime:
    settings = settings or get_settings()
    session_factory = build_session_factory(settings)
    repository = JobRepository(session_factory)
    llm_client = LLMClient(
        provider=DeepSeekProvider(settings=settings),
        settings=settings,
    )
    short_term_memory = ShortTermMemoryService(session_factory, settings=settings)
    memory_service = MemoryService(
        session_factory=session_factory,
        llm_client=llm_client,
        settings=settings,
    )
    summary_service = ConversationSummaryService(
        session_factory,
        llm_client=llm_client,
        settings=settings,
    )
    cleanup_service = CleanupService(
        session_factory=session_factory,
        short_term_memory=short_term_memory,
        settings=settings,
    )
    runner = JobRunner(
        repository=repository,
        memory_service=memory_service,
        short_term_memory=short_term_memory,
        conversation_summary=summary_service,
        title_service=ConversationTitleService(session_factory),
        cleanup_service=cleanup_service,
        settings=settings,
        close_callback=llm_client.close,
    )
    return ChatbotRuntime(
        recovery_service=RecoveryService(session_factory, settings=settings),
        job_runner=runner,
        settings=settings,
    )
```

补齐上述代码所需的 imports，包括 `Callable`。`CleanupService` 自己根据 `chatbot_semantic_memory_enabled` 构造 semantic index；`ChatbotRuntime.stop()` 最后调用 runner 的 `close()`，关闭 runtime 创建的 `llm_client`。在 `main.py` lifespan 中：

```python
@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    runtime = build_chatbot_runtime()
    await runtime.start()
    try:
        yield
    finally:
        await runtime.stop()
```

- [ ] **Step 6: 把 stale recovery 改为 compare-and-set**

在 `RecoveryService` 增加：

```python
def _mark_stale_run(
    self,
    session: Session,
    *,
    run_id: str,
    message_id: str,
    stale_before: datetime,
    now: datetime,
) -> bool:
    result = session.execute(
        update(ChatbotLLMRun)
        .where(
            ChatbotLLMRun.id == run_id,
            ChatbotLLMRun.status.in_(("pending", "streaming")),
            ChatbotLLMRun.updated_at < stale_before,
        )
        .values(
            status="failed",
            error_code="CHATBOT_STALE_GENERATION",
            error_message="Generation expired before completion",
            completed_at=now,
            updated_at=now,
        )
    )
    if not result.rowcount:
        return False
    session.execute(
        update(ChatbotMessage)
        .where(
            ChatbotMessage.id == message_id,
            ChatbotMessage.status.in_(("pending", "streaming")),
        )
        .values(status="failed", error_code="CHATBOT_STALE_GENERATION", updated_at=now)
    )
    return True
```

`reap_stale_runs` 循环只通过该方法累计 recovered，不再直接修改已加载 ORM 对象。

- [ ] **Step 7: 运行 runtime/recovery 测试并提交**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_chatbot_runtime.py backend/tests/chatbot/test_stale_recovery.py -q
```

Expected: PASS。

```powershell
git add backend/app/chatbot/services/job_runner.py backend/app/chatbot/services/runtime.py backend/app/chatbot/services/recovery_service.py backend/app/main.py backend/app/core/config.py backend/.env.example backend/tests/chatbot/test_chatbot_runtime.py backend/tests/chatbot/test_stale_recovery.py
git commit -m "feat(chatbot): run durable recovery workers"
```

### Task 4: 用 durable cleanup 完成 Conversation/Memory 删除

**Files:**
- Create: `backend/app/chatbot/services/cleanup_service.py`
- Modify: `backend/app/chatbot/services/conversation_service.py`
- Modify: `backend/app/chatbot/services/memory_service.py`
- Modify: `backend/app/chatbot/repositories/memory_repository.py`
- Modify: `backend/app/chatbot/memory/short_term_memory.py`
- Create: `backend/tests/chatbot/test_cleanup_retry.py`
- Modify: `backend/tests/chatbot/test_data_cleanup.py`

**Interfaces:**
- Produces: `ShortTermMemoryService.clear_conversation(user_id, conversation_id) -> None`。
- Produces: `CleanupService.cleanup_conversation(payload)`、`cleanup_memory(payload)`、`mark_retry(payload)`。
- Consumes: `JobRepository.enqueue` 和 `SemanticMemoryIndex.delete_memory`。

- [ ] **Step 1: 写删除事务和外部失败重试测试**

在 `test_cleanup_retry.py` 建立 Conversation、active memory、fake Redis 和第一次 delete 抛错的 fake semantic index，断言：

```python
with factory() as session:
    result = conversation_service.delete_conversation(session, owner_id, conversation_id)
assert result.status == "deleted"
assert result.cleanup_status == "pending"

with factory() as session:
    memory = session.get(ChatbotMemory, memory_id)
    conversation = session.get(ChatbotConversation, conversation_id)
    job = session.scalar(select(ChatbotJob).where(ChatbotJob.kind == "cleanup_conversation"))
assert memory.status == "deleted"
assert memory.embedding_status == "deleted"
assert conversation.cleanup_status == "pending"
assert job is not None

runner.run_once(limit=10)
with factory() as session:
    assert session.get(ChatbotConversation, conversation_id).cleanup_status == "retry"

semantic_index.fail_delete = False
with factory() as session:
    session.execute(
        update(ChatbotJob)
        .where(ChatbotJob.id == job.id)
        .values(available_at=datetime.now(timezone.utc))
    )
    session.commit()
runner.run_once(limit=10)
with factory() as session:
    assert session.get(ChatbotConversation, conversation_id).cleanup_status == "completed"
```

另加 Memory API 删除测试：Chroma 抛错时响应仍为 200，`cleanup_status` 为 pending/retry，不能是 completed。

- [ ] **Step 2: 运行测试确认当前删除只写 backlog 日志且同步吞掉 Chroma 错误**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_cleanup_retry.py backend/tests/chatbot/test_data_cleanup.py -q
```

Expected: FAIL。

- [ ] **Step 3: 在删除事务中软删关联 memory 并入队**

将 `ConversationService.__init__` 改为明确注入 `JobRepository`；repository 只负责使用调用方传入的 transaction session 入队：

```python
def __init__(
    self,
    settings: Settings | None = None,
    *,
    job_repository: JobRepository | None = None,
) -> None:
    self.settings = settings or get_settings()
    self.job_repository = job_repository or JobRepository(
        build_session_factory(self.settings)
    )
```

`delete_conversation` 在 commit 前执行：

```python
memory_ids = list(
    session.scalars(
        select(ChatbotMemory.id).where(
            ChatbotMemory.user_id == user_id,
            ChatbotMemory.conversation_id == model.id,
            ChatbotMemory.deleted_at.is_(None),
        )
    )
)
now = _utcnow()
session.execute(
    update(ChatbotMemory)
    .where(
        ChatbotMemory.user_id == user_id,
        ChatbotMemory.conversation_id == model.id,
        ChatbotMemory.deleted_at.is_(None),
    )
    .values(status="deleted", embedding_status="deleted", deleted_at=now, updated_at=now)
)
self.job_repository.enqueue(
    session,
    kind="cleanup_conversation",
    dedup_key=f"cleanup-conversation:{model.id}",
    payload={
        "user_id": user_id,
        "conversation_id": model.id,
        "memory_ids": memory_ids,
    },
)
session.flush()
session.commit()
```

`MemoryService.delete_memory` 不再调用 repository 的独立事务和 `_sync_semantic_delete`。改为使用传入 session 锁 row、软删、入队、commit，并返回 pending：

```python
row = session.scalar(
    select(ChatbotMemory)
    .where(
        ChatbotMemory.id == memory_id,
        ChatbotMemory.user_id == user_id,
        ChatbotMemory.deleted_at.is_(None),
    )
    .with_for_update()
)
if row is None:
    raise ChatbotApiError(
        status_code=404,
        code="CHATBOT_MEMORY_NOT_FOUND",
        message="Memory not found",
    )
now = _utcnow()
row.status = "deleted"
row.embedding_status = "deleted"
row.deleted_at = now
row.updated_at = now
self.job_repository.enqueue(
    session,
    kind="cleanup_memory",
    dedup_key=f"cleanup-memory:{row.id}",
    payload={"user_id": user_id, "memory_id": row.id},
)
session.commit()
return DeleteResultData(id=row.id, status="deleted", cleanup_status="pending")
```

`MemoryService` 的实际构造函数改为：

```python
def __init__(
    self,
    session_factory: sessionmaker[Session] | None = None,
    *,
    extractor: MemoryExtractor | None = None,
    llm_client: LLMClient | None = None,
    settings: Settings | None = None,
    repository: MemoryRepository | None = None,
    semantic_index: SemanticMemoryIndex | None = None,
    job_repository: JobRepository | None = None,
) -> None:
    self.settings = settings or get_settings()
    self.session_factory = session_factory or build_session_factory(self.settings)
    self.repository = repository or MemoryRepository(self.session_factory)
    self.extractor = extractor or MemoryExtractor(llm_client=llm_client, settings=self.settings)
    self.semantic_index = semantic_index
    if self.semantic_index is None and self.settings.chatbot_semantic_memory_enabled:
        self.semantic_index = SemanticMemoryIndex(settings=self.settings)
    self._queue: Queue[_WorkItem | None] = Queue(maxsize=100)
    self._worker_started = False
    self._worker_lock = Lock()
    self._stop_event = Event()
    self.job_repository = job_repository or JobRepository(self.session_factory)
```

- [ ] **Step 4: 增加 Redis 精确清理和 CleanupService**

在 `ShortTermMemoryService` 增加：

```python
def clear_conversation(self, user_id: str, conversation_id: str) -> None:
    if not self.settings.redis_url:
        return
    if self._adapter is None:
        raise RuntimeError("Redis short-term memory is unavailable")
    for memory_type in ("summary", "recent", "state"):
        self._adapter.delete(
            user_id=user_id,
            conversation_id=conversation_id,
            memory_type=memory_type,
        )
```

创建 `CleanupService`，构造函数和方法为：

```python
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker

from app.chatbot.memory.semantic_memory import SemanticMemoryIndex
from app.chatbot.memory.short_term_memory import ShortTermMemoryService
from app.chatbot.models.conversation import ChatbotConversation
from app.core.config import Settings, get_settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CleanupService:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        short_term_memory: ShortTermMemoryService,
        settings: Settings | None = None,
        semantic_index: SemanticMemoryIndex | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.short_term_memory = short_term_memory
        self.settings = settings or get_settings()
        self.semantic_index = semantic_index
        if self.semantic_index is None and self.settings.chatbot_semantic_memory_enabled:
            self.semantic_index = SemanticMemoryIndex(settings=self.settings)

    def cleanup_memory(self, payload: Mapping[str, object]) -> None:
        if self.semantic_index is not None and self.semantic_index.enabled:
            self.semantic_index.delete_memory(str(payload["memory_id"]))

    def cleanup_conversation(self, payload: Mapping[str, object]) -> None:
        user_id = str(payload["user_id"])
        conversation_id = str(payload["conversation_id"])
        self.short_term_memory.clear_conversation(user_id, conversation_id)
        if self.semantic_index is not None and self.semantic_index.enabled:
            for memory_id in payload.get("memory_ids", []):
                self.semantic_index.delete_memory(str(memory_id))
        with self.session_factory() as session:
            session.execute(
                update(ChatbotConversation)
                .where(
                    ChatbotConversation.id == conversation_id,
                    ChatbotConversation.user_id == user_id,
                    ChatbotConversation.status == "deleted",
                )
                .values(cleanup_status="completed", updated_at=_utcnow())
            )
            session.commit()

    def mark_retry(self, payload: Mapping[str, object]) -> None:
        conversation_id = payload.get("conversation_id")
        if conversation_id is None:
            return
        user_id = str(payload["user_id"])
        with self.session_factory() as session:
            session.execute(
                update(ChatbotConversation)
                .where(
                    ChatbotConversation.id == str(conversation_id),
                    ChatbotConversation.user_id == user_id,
                    ChatbotConversation.status == "deleted",
                )
                .values(cleanup_status="retry", updated_at=_utcnow())
            )
            session.commit()
```

所有 delete 操作天然幂等，job 重放可以重复执行。

- [ ] **Step 5: 防御性排除 deleted Conversation memories**

在 `MemoryRepository.list_owned_page` 的主查询加入 outer join：

```python
stmt = (
    select(ChatbotMemory)
    .outerjoin(ChatbotConversation, ChatbotConversation.id == ChatbotMemory.conversation_id)
    .where(
        ChatbotMemory.user_id == user_id,
        ChatbotMemory.deleted_at.is_(None),
        or_(
            ChatbotMemory.conversation_id.is_(None),
            ChatbotConversation.deleted_at.is_(None),
        ),
    )
)
```

导入 `ChatbotConversation`。这样旧数据即使尚未被 cleanup 补偿，也不能进入 `ContextService._long_term_sections`。

- [ ] **Step 6: 运行 cleanup/context 测试并提交**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_cleanup_retry.py backend/tests/chatbot/test_data_cleanup.py backend/tests/chatbot/test_context_service.py backend/tests/chatbot/test_memory_api.py -q
```

Expected: PASS。

```powershell
git add backend/app/chatbot/services/cleanup_service.py backend/app/chatbot/services/conversation_service.py backend/app/chatbot/services/memory_service.py backend/app/chatbot/repositories/memory_repository.py backend/app/chatbot/memory/short_term_memory.py backend/tests/chatbot/test_cleanup_retry.py backend/tests/chatbot/test_data_cleanup.py
git commit -m "fix(chatbot): make deletion cleanup durable"
```

### Task 5: Redis 运行期故障降级

**Files:**
- Modify: `backend/app/chatbot/services/cancellation_service.py`
- Modify: `backend/app/chatbot/services/concurrency_service.py`
- Create: `backend/tests/chatbot/test_redis_degradation.py`

**Interfaces:**
- Produces: Cancellation 的 Redis get/set/delete 失败后转进程内 store。
- Produces: Concurrency acquire 失败后转进程内 lease；renew/release 失败返回 false，不抛出。
- Consumes: `log_chatbot_event`，事件名固定为 `chatbot.redis.degraded`，字段为 source、operation、reason、status。

- [ ] **Step 1: 写初始化、运行期和 release 故障测试**

创建 fake Redis client，其 `ping` 可成功，但 `get/set/eval/delete` 按 operation 抛 `RuntimeError`：

```python
from types import SimpleNamespace


class FakeRedisClient:
    def __init__(self, fail: set[str]) -> None:
        self.fail = set(fail)
        self.values: dict[str, str] = {}

    def _check(self, operation: str) -> None:
        if operation in self.fail:
            raise RuntimeError(f"redis {operation} unavailable")

    def ping(self) -> None:
        self._check("ping")

    def get(self, key: str):
        self._check("get")
        return self.values.get(key)

    def set(self, key: str, value: str, **kwargs):
        self._check("set")
        if kwargs.get("nx") and key in self.values:
            return False
        self.values[key] = value
        return True

    def eval(self, script: str, key_count: int, key: str, owner: str, *args):
        self._check("eval")
        if self.values.get(key) != owner:
            return 0
        if "del" in script:
            self.values.pop(key, None)
        return 1

    def delete(self, key: str):
        self._check("delete")
        return int(self.values.pop(key, None) is not None)


class FakeRedisModule:
    def __init__(self, fail: set[str]) -> None:
        self.client = FakeRedisClient(fail)

    def from_url(self, url: str, decode_responses: bool):
        return self.client


def _redis_settings() -> Settings:
    return Settings(redis_url="redis://example.invalid/0", chatbot_lock_ttl_seconds=90)
```

测试：

```python
def test_cancellation_falls_back_when_redis_fails_mid_request() -> None:
    service = CancellationService(settings=_redis_settings(), redis_module=FakeRedisModule(fail={"set"}))
    record = service.request_stop("conv-1", "assistant-1")
    assert record.status == "cancellation_requested"
    assert service.is_requested("conv-1", "assistant-1") is True


def test_concurrency_falls_back_and_release_never_raises() -> None:
    module = FakeRedisModule(fail={"set"})
    service = ConcurrencyService(settings=_redis_settings(), redis_module=module)
    lease = service.acquire("conv-1", "user-1")
    assert lease is not None
    assert lease.backend == "memory"
    assert service.release(lease) is True

    redis_module = FakeRedisModule(fail=set())
    redis_service = ConcurrencyService(settings=_redis_settings(), redis_module=redis_module)
    redis_lease = redis_service.acquire("conv-2", "user-1")
    assert redis_lease is not None
    assert redis_lease.backend == "redis"
    redis_module.client.fail = {"eval"}
    assert redis_service.release(redis_lease) is False
```

另写 init `ping` 抛错测试，Cancellation 构造不能再抛。

- [ ] **Step 2: 运行测试确认 Cancellation init/runtime 仍抛异常**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_redis_degradation.py -q
```

Expected: FAIL。

- [ ] **Step 3: 实现 Cancellation 降级**

把 Cancellation 构造连接放入 try/except，并增加：

```python
def _degrade(self, operation: str, exc: Exception) -> None:
    self._client = None
    log_chatbot_event(
        "chatbot.redis.degraded",
        source="cancellation",
        operation=operation,
        reason=type(exc).__name__,
        status="memory_fallback",
    )
```

每个 Redis 操作使用：

```python
if self._client is not None:
    try:
        # 原 get/set/delete
    except Exception as exc:
        self._degrade("get|set|delete", exc)
# 紧接着执行现有 memory_store 路径
```

不得在异常后直接 return；`request_stop` 必须把同一 cancellation record 写入本地 store。

- [ ] **Step 4: 实现 Concurrency 降级**

增加同样的 `_degrade`，source 为 `concurrency`。`acquire` 的 Redis set 失败后继续执行现有 memory lease 分支。`renew` 和 `release` 的 Redis eval 失败时：

- 如果 lease.backend 为 memory，继续本地分支。
- 如果 lease.backend 为 redis，记录降级并返回 false；不得伪造释放成功，也不得抛出覆盖业务结果。

构造 lease 时不要依赖动态 `backend_name`；为 `_build_lease` 增加显式 `backend` 参数，Redis 成功传 `"redis"`，本地成功传 `"memory"`。

- [ ] **Step 5: 运行 Redis、并发和停止测试**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_redis_degradation.py backend/tests/chatbot/test_concurrency.py backend/tests/chatbot/test_generation_controls.py -q
```

Expected: PASS。

- [ ] **Step 6: 提交 Task 5**

```powershell
git add backend/app/chatbot/services/cancellation_service.py backend/app/chatbot/services/concurrency_service.py backend/tests/chatbot/test_redis_degradation.py
git commit -m "fix(chatbot): degrade Redis runtime failures"
```

### Task 6: Phase B 集成门禁

**Files:**
- Verify only; only fix regressions attributable to Tasks 1–5.

**Interfaces:**
- Produces: migration、完成链路、worker、cleanup、Redis 降级共同通过。

- [ ] **Step 1: 运行阶段核心测试**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_job_repository.py backend/tests/chatbot/test_completion_jobs.py backend/tests/chatbot/test_chatbot_runtime.py backend/tests/chatbot/test_cleanup_retry.py backend/tests/chatbot/test_redis_degradation.py -q
```

Expected: PASS。

- [ ] **Step 2: 运行完整 Chatbot 后端测试**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot -q
```

Expected: 全部 PASS，0 failed。

- [ ] **Step 3: 验证 migration 链**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini heads
```

Expected: 唯一 head 为 `0007_create_chatbot_jobs`。

- [ ] **Step 4: 检查 diff**

```powershell
git diff --check
git status --short
```

Expected: 无空白错误，只包含本计划声明的后端、migration、env example 和测试文件。
