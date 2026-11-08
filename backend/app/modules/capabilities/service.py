from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.capabilities.models import (
    CapabilityDefinition,
    CapabilityDependency,
    CapabilityGrant,
    CapabilityReview,
    CapabilityRun,
    CapabilityVersion,
)
from app.modules.capabilities.schemas import (
    CapabilityCreate,
    CapabilityDetail,
    CapabilitySnapshot,
    CapabilitySummary,
    CapabilityUpdate,
    CapabilityVersionView,
    PublicCapability,
)
from app.modules.capabilities.seed import DEMO_CAPABILITIES
from app.modules.identity.models import User
from app.modules.observability.models import AuditEvent
from app.repositories import utc_now
from app.config import settings

VALID_KINDS = {"tool", "skill", "mcp", "agent"}


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def loads(value: str, default: Any = None) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def aware(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=timezone.utc) if value is not None else None


def snapshot_view(version: CapabilityVersion) -> CapabilityVersionView:
    snapshot = CapabilitySnapshot.model_validate(loads(version.snapshot_json, {}))
    return CapabilityVersionView(
        id=version.id,
        version=version.version,
        status=version.status,
        snapshot=snapshot,
        changelog=version.changelog,
        createdBy=version.created_by,
        publishedBy=version.published_by,
        createdAt=aware(version.created_at),
        publishedAt=aware(version.published_at),
        retiredAt=aware(version.retired_at),
    )


def latest_version(versions: list[CapabilityVersion], status: str) -> CapabilityVersion | None:
    matches = [version for version in versions if version.status == status]
    return max(matches, key=lambda version: version.version, default=None)


def latest_draft(versions: list[CapabilityVersion]) -> CapabilityVersion | None:
    return latest_version(versions, "draft")


def latest_published(versions: list[CapabilityVersion]) -> CapabilityVersion | None:
    return latest_version(versions, "published")


def summary_view(definition: CapabilityDefinition) -> CapabilitySummary:
    published = latest_published(definition.versions)
    draft = latest_draft(definition.versions)
    snapshot = (
        loads(published.snapshot_json, {})
        if published is not None
        else loads(draft.snapshot_json, {}) if draft is not None else {}
    )
    return CapabilitySummary(
        id=definition.id,
        slug=definition.slug,
        kind=definition.kind,
        name=definition.name,
        description=definition.description,
        category=definition.category,
        icon=definition.icon,
        status=definition.status,
        source=definition.source,
        hasDraft=draft is not None,
        publishedVersion=published.version if published else None,
        draftVersion=draft.version if draft else None,
        executionMode=snapshot.get("executionMode"),
        visibility=definition.visibility,
        accessMode=definition.access_mode,
        reviewStatus=definition.review_status,
        ownerId=definition.owner_id,
        testStatus=definition.test_status,
        updatedAt=aware(definition.updated_at),
    )


def detail_view(definition: CapabilityDefinition) -> CapabilityDetail:
    summary = summary_view(definition)
    published = latest_published(definition.versions)
    draft = latest_draft(definition.versions)
    return CapabilityDetail(
        **summary.model_dump(),
        createdAt=aware(definition.created_at),
        createdBy=definition.created_by,
        draft=snapshot_view(draft) if draft else None,
        published=snapshot_view(published) if published else None,
        versions=[snapshot_view(version) for version in reversed(definition.versions)],
    )


def public_view(
    definition: CapabilityDefinition,
    version: CapabilityVersion,
    *,
    authorized: bool = True,
    blocked_reason: str = "none",
    primary_action: str = "use",
) -> PublicCapability:
    snapshot = CapabilitySnapshot.model_validate(loads(version.snapshot_json, {}))
    return PublicCapability(
        id=definition.id,
        kind=definition.kind,
        name=snapshot.name,
        description=snapshot.description,
        category=snapshot.category,
        icon=snapshot.icon,
        source="system" if snapshot.source == "system" else "managed",
        steps=snapshot.steps,
        tools=snapshot.tools,
        content=snapshot.content,
        executionMode=snapshot.executionMode,
        visibility=definition.visibility,
        accessMode=definition.access_mode,
        authorized=authorized,
        ready=definition.test_status == "passed" and definition.status == "published",
        testStatus=definition.test_status,
        blockedReason=blocked_reason,
        primaryAction=primary_action,
        version=version.version,
        versionId=version.id,
    )


class CapabilityService:
    def __init__(self, session: Session):
        self.session = session

    def ensure_demo_catalog(self) -> None:
        now = utc_now()
        existing = set(self.session.scalars(select(CapabilityDefinition.id)))
        created = False
        for capability_id, kind, name, category, description, icon, steps, tools in DEMO_CAPABILITIES:
            if capability_id in existing:
                continue
            definition = CapabilityDefinition(
                id=capability_id,
                slug=capability_id,
                kind=kind,
                name=name,
                description=description,
                category=category,
                icon=icon,
                status="published",
                source="demo",
                created_by="system",
                created_at=now,
                updated_at=now,
            )
            snapshot = CapabilitySnapshot(
                kind=kind,
                name=name,
                description=description,
                category=category,
                icon=icon,
                steps=steps,
                tools=tools or [],
                content=None,
                config={"executor": "demo", "runtime": "not-connected"},
                executionMode="demo",
                source="system",
            )
            version = CapabilityVersion(
                capability_id=capability_id,
                version=1,
                status="published",
                snapshot_json=dumps(snapshot.model_dump()),
                changelog="系统初始化演示能力",
                created_by="system",
                published_by="system",
                created_at=now,
                published_at=now,
            )
            definition.versions.append(version)
            self.session.add(definition)
            created = True
        if created:
            self.session.commit()

    def _get(self, capability_id: str, *, with_versions: bool = True) -> CapabilityDefinition:
        statement = select(CapabilityDefinition).where(CapabilityDefinition.id == capability_id)
        if with_versions:
            statement = statement.options(selectinload(CapabilityDefinition.versions))
        definition = self.session.scalar(statement)
        if definition is None:
            raise HTTPException(status_code=404, detail="Capability not found")
        return definition

    def list(
        self,
        *,
        kind: str | None,
        status: str | None,
        query: str,
        limit: int = 200,
    ) -> list[CapabilitySummary]:
        statement = select(CapabilityDefinition).options(
            selectinload(CapabilityDefinition.versions)
        )
        if kind:
            statement = statement.where(CapabilityDefinition.kind == kind)
        if status:
            statement = statement.where(CapabilityDefinition.status == status)
        if query.strip():
            value = f"%{query.strip()}%"
            statement = statement.where(
                CapabilityDefinition.name.ilike(value)
                | CapabilityDefinition.description.ilike(value)
                | CapabilityDefinition.category.ilike(value)
            )
        definitions = list(
            self.session.scalars(
                statement.order_by(
                    CapabilityDefinition.updated_at.desc(), CapabilityDefinition.id
                ).limit(limit)
            )
        )
        return [summary_view(definition) for definition in definitions]

    def list_owned(self, owner_id: str) -> list[CapabilitySummary]:
        definitions = list(
            self.session.scalars(
                select(CapabilityDefinition)
                .where(CapabilityDefinition.owner_id == owner_id)
                .options(selectinload(CapabilityDefinition.versions))
                .order_by(CapabilityDefinition.updated_at.desc())
            )
        )
        return [summary_view(definition) for definition in definitions]

    def detail(self, capability_id: str) -> CapabilityDetail:
        return detail_view(self._get(capability_id))

    def create(
        self,
        payload: CapabilityCreate,
        *,
        actor_id: str,
        owner_id: str | None = None,
        visibility: str = "platform",
        access_mode: str = "all_active",
        review_status: str = "none",
        source: str = "admin",
    ) -> CapabilityDetail:
        now = utc_now()
        slug = f"{payload.kind}-{uuid4().hex[:12]}"
        definition = CapabilityDefinition(
            slug=slug,
            kind=payload.kind,
            name=payload.name.strip(),
            description=payload.description.strip(),
            category=payload.category.strip(),
            icon=payload.icon.strip(),
            status="draft",
            source=source,
            created_by=actor_id,
            owner_id=owner_id,
            visibility=visibility,
            access_mode=access_mode,
            review_status=review_status,
            created_at=now,
            updated_at=now,
        )
        snapshot = CapabilitySnapshot(
            kind=payload.kind,
            name=payload.name,
            description=payload.description,
            category=payload.category,
            icon=payload.icon,
            steps=payload.steps,
            tools=payload.tools,
            content=payload.content,
            config=payload.config,
            executionMode="simulated",
            source="managed",
        )
        version = CapabilityVersion(
            version=1,
            status="draft",
            snapshot_json=dumps(snapshot.model_dump()),
            changelog=payload.changelog or "创建能力草稿",
            created_by=actor_id,
            created_at=now,
        )
        definition.versions.append(version)
        self.session.add(definition)
        self.session.flush()
        return detail_view(self._get(definition.id))

    def update(
        self, capability_id: str, payload: CapabilityUpdate, *, actor_id: str
    ) -> CapabilityDetail:
        definition = self._get(capability_id)
        draft = latest_draft(definition.versions)
        if draft is not None and payload.draftVersionId not in {None, draft.id}:
            raise HTTPException(
                status_code=409, detail="Capability draft was updated by another session"
            )
        if draft is None:
            base = latest_published(definition.versions)
            base_snapshot = (
                CapabilitySnapshot.model_validate(loads(base.snapshot_json, {}))
                if base is not None
                else CapabilitySnapshot(
                    kind=definition.kind,
                    name=definition.name,
                    description=definition.description,
                    category=definition.category,
                    icon=definition.icon,
                    executionMode="simulated",
                    source="managed",
                )
            )
            draft = CapabilityVersion(
                version=max((item.version for item in definition.versions), default=0) + 1,
                status="draft",
                snapshot_json=dumps(base_snapshot.model_dump()),
                changelog="从现有版本创建编辑草稿",
                created_by=actor_id,
                created_at=utc_now(),
            )
            definition.versions.append(draft)

        snapshot = CapabilitySnapshot.model_validate(loads(draft.snapshot_json, {}))
        updates = payload.model_dump(
            exclude={"draftVersionId", "changelog"}, exclude_unset=True
        )
        for field, value in updates.items():
            if value is not None:
                setattr(snapshot, field, value)
        draft.snapshot_json = dumps(snapshot.model_dump())
        if payload.changelog is not None:
            draft.changelog = payload.changelog
        definition.name = snapshot.name
        definition.description = snapshot.description
        definition.category = snapshot.category
        definition.icon = snapshot.icon
        definition.updated_at = utc_now()
        self.session.flush()
        return detail_view(self._get(capability_id))

    def publish(
        self,
        capability_id: str,
        *,
        version_id: str | None,
        changelog: str,
        actor_id: str,
    ) -> CapabilityDetail:
        definition = self._get(capability_id)
        if definition.review_status == "submitted":
            raise HTTPException(status_code=409, detail="Capability is awaiting review")
        if definition.source == "creator" and definition.review_status != "approved":
            raise HTTPException(status_code=409, detail="Creator capability requires approval")
        draft = next(
            (item for item in definition.versions if version_id and item.id == version_id),
            None,
        ) or latest_draft(definition.versions)
        if draft is None or draft.status != "draft":
            raise HTTPException(status_code=409, detail="No editable draft to publish")
        snapshot = CapabilitySnapshot.model_validate(loads(draft.snapshot_json, {}))
        if not snapshot.name.strip():
            raise HTTPException(status_code=422, detail="Capability name is required")
        self._lock_dependencies(definition, draft, snapshot)
        now = utc_now()
        for item in definition.versions:
            if item.status == "published" and item.id != draft.id:
                item.status = "retired"
                item.retired_at = now
        draft.status = "published"
        draft.published_by = actor_id
        draft.published_at = now
        if changelog:
            draft.changelog = changelog
        definition.status = "published"
        definition.name = snapshot.name
        definition.description = snapshot.description
        definition.category = snapshot.category
        definition.icon = snapshot.icon
        definition.updated_at = now
        self._record_review(definition, draft.id, "publish", actor_id, changelog)
        return detail_view(self._get(capability_id))

    def _lock_dependencies(
        self,
        definition: CapabilityDefinition,
        version: CapabilityVersion,
        snapshot: CapabilitySnapshot,
    ) -> None:
        self.session.execute(
            delete(CapabilityDependency).where(
                CapabilityDependency.version_id == version.id
            )
        )
        raw = snapshot.config.get("dependencies", [])
        if raw is None:
            return
        if not isinstance(raw, list):
            raise HTTPException(status_code=422, detail="Dependencies must be a list")
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                raise HTTPException(status_code=422, detail="Dependency entry is invalid")
            dependency_id = str(item.get("id", "")).strip()
            dependency_version_id = str(item.get("versionId", "")).strip()
            kind = str(item.get("kind", "")).strip()
            if not dependency_id or not dependency_version_id:
                raise HTTPException(
                    status_code=422,
                    detail="Dependency requires id and versionId",
                )
            if dependency_id in seen:
                continue
            target = self.session.get(CapabilityVersion, dependency_version_id)
            target_definition = self.session.get(CapabilityDefinition, dependency_id)
            if (
                target is None
                or target.capability_id != dependency_id
                or target.status != "published"
                or target_definition is None
                or target_definition.status != "published"
            ):
                raise HTTPException(
                    status_code=422,
                    detail="Dependency version is not published or does not match",
                )
            if kind and kind != target_definition.kind:
                raise HTTPException(
                    status_code=422, detail="Dependency kind does not match"
                )
            seen.add(dependency_id)
            self.session.add(
                CapabilityDependency(
                    version_id=version.id,
                    dependency_id=dependency_id,
                    dependency_kind=target_definition.kind,
                    dependency_version_id=target.id,
                )
            )

    def disable(self, capability_id: str, *, actor_id: str) -> CapabilityDetail:
        definition = self._get(capability_id)
        published = latest_published(definition.versions)
        if published is None:
            raise HTTPException(status_code=409, detail="Capability has no published version")
        now = utc_now()
        published.status = "retired"
        published.retired_at = now
        definition.status = "disabled"
        definition.updated_at = now
        self._record_review(definition, published.id, "disable", actor_id, "")
        return detail_view(self._get(capability_id))

    def _record_review(
        self,
        definition: CapabilityDefinition,
        version_id: str,
        action: str,
        actor_id: str,
        reason: str,
    ) -> CapabilityReview:
        event = CapabilityReview(
            capability_id=definition.id,
            version_id=version_id,
            action=action,
            actor_id=actor_id,
            reason=(reason or "")[:255],
            created_at=utc_now(),
        )
        self.session.add(event)
        return event

    def submit(
        self, capability_id: str, *, actor_id: str, reason: str = ""
    ) -> CapabilityDetail:
        definition = self._get(capability_id)
        if definition.owner_id not in {None, actor_id}:
            raise HTTPException(status_code=403, detail="Only the owner can submit")
        draft = latest_draft(definition.versions)
        if draft is None:
            raise HTTPException(status_code=409, detail="No draft to submit")
        if definition.test_status != "passed":
            raise HTTPException(status_code=409, detail="Capability must pass its test first")
        definition.review_status = "submitted"
        definition.submitted_by = actor_id
        definition.submitted_at = utc_now()
        definition.review_reason = reason[:255]
        self._record_review(definition, draft.id, "submit", actor_id, reason)
        self.session.commit()
        return detail_view(self._get(capability_id))

    def review(
        self,
        capability_id: str,
        action: str,
        *,
        actor_id: str,
        reason: str = "",
    ) -> CapabilityDetail:
        if action not in {"approve", "reject"}:
            raise HTTPException(status_code=400, detail="Unknown review action")
        definition = self._get(capability_id)
        if definition.review_status != "submitted":
            raise HTTPException(status_code=409, detail="Capability is not awaiting review")
        draft = latest_draft(definition.versions)
        now = utc_now()
        definition.review_status = "approved" if action == "approve" else "rejected"
        definition.reviewed_by = actor_id
        definition.reviewed_at = now
        definition.review_reason = reason[:255]
        self._record_review(definition, draft.id if draft else "", action, actor_id, reason)
        self.session.commit()
        return detail_view(self._get(capability_id))

    def test_capability(
        self, capability_id: str, *, actor_id: str
    ) -> CapabilityDetail:
        definition = self._get(capability_id)
        draft = latest_draft(definition.versions) or latest_published(definition.versions)
        if draft is None:
            raise HTTPException(status_code=409, detail="Capability has no testable version")
        snapshot = CapabilitySnapshot.model_validate(loads(draft.snapshot_json, {}))
        checks: list[dict[str, Any]] = []
        checks.append({"name": "name", "ok": bool(snapshot.name.strip())})
        executor = str(snapshot.config.get("executor", "")).strip().lower()
        is_agent = snapshot.kind == "agent"
        checks.append(
            {
                "name": "executor",
                "ok": is_agent or executor in {"system", "mcp", "demo"},
            }
        )
        tool_name = str(snapshot.config.get("tool", "")).strip()
        ready = False
        if is_agent:
            raw = snapshot.config.get("dependencies", [])
            dependency_checks: list[dict[str, Any]] = []
            valid = isinstance(raw, list) and bool(raw)
            if isinstance(raw, list):
                for item in raw:
                    if not isinstance(item, dict):
                        valid = False
                        continue
                    dependency_id = str(item.get("id", "")).strip()
                    dependency_version_id = str(item.get("versionId", "")).strip()
                    target = (
                        self.session.get(CapabilityVersion, dependency_version_id)
                        if dependency_version_id
                        else None
                    )
                    target_definition = (
                        self.session.get(CapabilityDefinition, dependency_id)
                        if dependency_id
                        else None
                    )
                    ok = bool(
                        target
                        and target.capability_id == dependency_id
                        and target.status == "published"
                        and target_definition
                        and target_definition.status == "published"
                    )
                    valid = valid and ok
                    dependency_checks.append(
                        {
                            "id": dependency_id,
                            "versionId": dependency_version_id,
                            "ok": ok,
                        }
                    )
            ready = valid
            checks.append(
                {
                    "name": "agent-dependencies",
                    "ok": ready,
                    "detail": dependency_checks,
                }
            )
        elif executor == "system":
            from app.modules.runtime.tools import get_tool

            tool = get_tool(tool_name)
            ready = tool is not None and not tool.side_effect
            checks.append({"name": "readonly-tool", "ok": ready, "detail": tool_name})
        elif executor == "mcp":
            from app.modules.personal.models import McpServer

            server_id = str(snapshot.config.get("mcpServerId", "")).strip()
            mcp_tool = str(snapshot.config.get("mcpTool", "")).strip()
            server = self.session.get(McpServer, server_id) if server_id else None
            tools = loads(server.tools_json, []) if server is not None else []
            tool_names = {
                str(item.get("name", "")).strip()
                for item in tools
                if isinstance(item, dict)
            }
            ready = (
                server is not None
                and server.status == "approved"
                and bool(mcp_tool)
                and mcp_tool in tool_names
            )
            checks.append(
                {
                    "name": "approved-mcp-tool",
                    "ok": ready,
                    "detail": f"{server_id}:{mcp_tool}",
                }
            )
        elif executor == "demo":
            ready = False
            checks.append(
                {"name": "demo-isolation", "ok": False, "detail": "Demo cannot pass production readiness"}
            )
        else:
            checks.append({"name": "executor", "ok": False, "detail": executor})
        definition.test_status = "passed" if ready else "failed"
        definition.tested_at = utc_now()
        definition.test_detail_json = dumps({"checks": checks})
        self._record_review(
            definition,
            draft.id,
            "test",
            actor_id,
            "passed" if ready else "failed",
        )
        self.session.commit()
        return detail_view(self._get(capability_id))

    def rollback(
        self, capability_id: str, version_id: str, *, actor_id: str
    ) -> CapabilityDetail:
        definition = self._get(capability_id)
        target = next((item for item in definition.versions if item.id == version_id), None)
        if target is None or target.status not in {"published", "retired"}:
            raise HTTPException(status_code=404, detail="Rollback version not found")
        now = utc_now()
        for item in definition.versions:
            if item.status == "published" and item.id != target.id:
                item.status = "retired"
                item.retired_at = now
        target.status = "published"
        target.published_at = target.published_at or now
        definition.status = "published"
        definition.updated_at = now
        self._record_review(definition, target.id, "rollback", actor_id, "")
        self.session.commit()
        return detail_view(self._get(capability_id))

    def grant(
        self, capability_id: str, user_id: str, *, actor_id: str
    ) -> None:
        definition = self._get(capability_id)
        user = self.session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        existing = self.session.scalar(
            select(CapabilityGrant).where(
                CapabilityGrant.capability_id == definition.id,
                CapabilityGrant.user_id == user_id,
            )
        )
        if existing is None:
            self.session.add(
                CapabilityGrant(
                    capability_id=definition.id,
                    user_id=user_id,
                    granted_by=actor_id,
                    created_at=utc_now(),
                )
            )
        self._record_review(definition, "", "grant", actor_id, user_id)
        self.session.commit()

    def revoke_grant(self, capability_id: str, user_id: str, *, actor_id: str) -> None:
        definition = self._get(capability_id)
        grant = self.session.scalar(
            select(CapabilityGrant).where(
                CapabilityGrant.capability_id == definition.id,
                CapabilityGrant.user_id == user_id,
            )
        )
        if grant is None:
            raise HTTPException(status_code=404, detail="Grant not found")
        self.session.delete(grant)
        self._record_review(definition, "", "revoke-grant", actor_id, user_id)
        self.session.commit()

    def list_reviews(self, limit: int = 100) -> list[CapabilityReview]:
        return list(
            self.session.scalars(
                select(CapabilityReview)
                .order_by(CapabilityReview.created_at.desc())
                .limit(limit)
            )
        )

    def _user(self, user_id: str | None) -> User | None:
        return self.session.get(User, user_id) if user_id else None

    def can_execute(self, definition: CapabilityDefinition, user_id: str | None) -> bool:
        if definition.status != "published":
            return False
        if definition.source == "demo":
            return True
        if not user_id:
            return False
        user = self._user(user_id)
        if user is None or user.status != "ACTIVE":
            return False
        if definition.owner_id == user_id:
            return True
        if definition.access_mode == "all_active":
            return True
        return (
            self.session.scalar(
                select(CapabilityGrant.id).where(
                    CapabilityGrant.capability_id == definition.id,
                    CapabilityGrant.user_id == user_id,
                )
            )
            is not None
        )

    def _runs_today(self, user_id: str | None) -> bool:
        if not user_id:
            return False
        from app.modules.runtime.models import AgentRun

        since = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        used = self.session.scalar(
            select(func.count(AgentRun.id)).where(
                AgentRun.user_id == user_id,
                AgentRun.created_at >= since,
            )
        )
        return (used or 0) >= settings.llm_daily_request_limit

    def _has_mcp_connection(self, user_id: str | None, server_id: str) -> bool:
        if not user_id or not server_id:
            return True
        from app.modules.personal.models import McpConnection

        return (
            self.session.scalar(
                select(McpConnection.id).where(
                    McpConnection.user_id == user_id,
                    McpConnection.server_id == server_id,
                    McpConnection.status == "connected",
                )
            )
            is not None
        )

    def _availability(
        self,
        definition: CapabilityDefinition,
        user_id: str | None,
        *,
        authorized: bool,
        budget_exhausted: bool,
    ) -> tuple[str, str]:
        if definition.source == "demo":
            return "none", "use"
        if not user_id:
            return "login_required", "login"
        user = self._user(user_id)
        if user is None or user.status != "ACTIVE":
            return "account_inactive", "activate"
        if not authorized:
            return "no_permission", "request_access"
        version = latest_published(definition.versions)
        config = (
            CapabilitySnapshot.model_validate(loads(version.snapshot_json, {})).config
            if version is not None
            else {}
        )
        server_id = str(config.get("mcpServerId", "")).strip()
        if server_id and not self._has_mcp_connection(user_id, server_id):
            return "needs_mcp_connection", "connect"
        if definition.test_status != "passed":
            return "not_ready", "unavailable"
        if budget_exhausted:
            return "budget_exhausted", "budget"
        return "none", "use"

    def public_list(
        self,
        *,
        kind: str | None = None,
        query: str = "",
        user_id: str | None = None,
    ) -> list[PublicCapability]:
        statement = (
            select(CapabilityDefinition)
            .where(CapabilityDefinition.status == "published")
            .options(selectinload(CapabilityDefinition.versions))
        )
        if kind:
            statement = statement.where(CapabilityDefinition.kind == kind)
        if query.strip():
            value = f"%{query.strip()}%"
            statement = statement.where(
                CapabilityDefinition.name.ilike(value)
                | CapabilityDefinition.description.ilike(value)
            )
        result: list[PublicCapability] = []
        budget_exhausted = self._runs_today(user_id)
        for definition in self.session.scalars(
            statement.order_by(CapabilityDefinition.updated_at.desc())
        ):
            if definition.source == "demo" and not settings.demo_catalog_enabled:
                continue
            if definition.visibility == "private" and definition.owner_id != user_id:
                continue
            authorized = self.can_execute(definition, user_id)
            if definition.access_mode == "granted" and not authorized:
                user = self._user(user_id)
                if user is None or user.status != "ACTIVE":
                    continue
            reason, action = self._availability(
                definition,
                user_id,
                authorized=authorized,
                budget_exhausted=budget_exhausted,
            )
            version = latest_published(definition.versions)
            if version is not None:
                result.append(
                    public_view(
                        definition,
                        version,
                        authorized=authorized,
                        blocked_reason=reason,
                        primary_action=action,
                    )
                )
        return result

    def resolve_published(
        self, capability_id: str, kind: str | None = None
    ) -> tuple[CapabilityDefinition, CapabilityVersion, PublicCapability]:
        definition = self.session.scalar(
            select(CapabilityDefinition)
            .where(CapabilityDefinition.id == capability_id)
            .options(selectinload(CapabilityDefinition.versions))
        )
        if definition is None or definition.status != "published":
            raise HTTPException(status_code=422, detail="能力未发布、已停用或不存在")
        if kind is not None and definition.kind != kind:
            raise HTTPException(status_code=422, detail="能力类型不匹配")
        version = latest_published(definition.versions)
        if version is None:
            raise HTTPException(status_code=422, detail="能力未发布、已停用或不存在")
        return definition, version, public_view(definition, version)

    def public_capability(
        self, capability_id: str, user_id: str | None = None
    ) -> PublicCapability:
        definition = self.session.scalar(
            select(CapabilityDefinition)
            .where(CapabilityDefinition.id == capability_id)
            .options(selectinload(CapabilityDefinition.versions))
        )
        if definition is None or definition.status != "published":
            raise HTTPException(status_code=404, detail="Capability not found")
        if definition.source == "demo" and not settings.demo_catalog_enabled:
            raise HTTPException(status_code=404, detail="Capability not found")
        if definition.visibility == "private" and definition.owner_id != user_id:
            raise HTTPException(status_code=404, detail="Capability not found")
        authorized = self.can_execute(definition, user_id)
        if definition.access_mode == "granted" and not authorized:
            user = self._user(user_id)
            if user is None or user.status != "ACTIVE":
                raise HTTPException(status_code=404, detail="Capability not found")
        reason, action = self._availability(
            definition,
            user_id,
            authorized=authorized,
            budget_exhausted=self._runs_today(user_id),
        )
        version = latest_published(definition.versions)
        if version is None:
            raise HTTPException(status_code=404, detail="Capability not found")
        return public_view(
            definition,
            version,
            authorized=authorized,
            blocked_reason=reason,
            primary_action=action,
        )

    def record_run(
        self,
        *,
        definition: CapabilityDefinition,
        version: CapabilityVersion,
        public: PublicCapability,
        conversation_id: str,
        owner_id: str,
    ) -> None:
        self.session.add(
            CapabilityRun(
                capability_id=definition.id,
                version_id=version.id,
                version=version.version,
                conversation_id=conversation_id,
                owner_id=owner_id,
                mode=public.executionMode,
                status="accepted",
                detail_json=dumps(
                    {
                        "capabilityName": public.name,
                        "kind": public.kind,
                        "source": public.source,
                    }
                ),
                created_at=utc_now(),
            )
        )


def encode_cursor(created_at: datetime, row_id: str) -> str:
    value = f"{created_at.isoformat()}|{row_id}".encode("utf-8")
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def decode_cursor(value: str) -> tuple[datetime, str]:
    try:
        padded = value + "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode(padded).decode("utf-8")
        timestamp, row_id = raw.split("|", 1)
        return datetime.fromisoformat(timestamp), row_id
    except (ValueError, UnicodeDecodeError) as error:
        raise HTTPException(status_code=400, detail="Invalid cursor") from error


def run_count(session: Session) -> int:
    return int(session.scalar(select(func.count()).select_from(CapabilityRun)) or 0)
