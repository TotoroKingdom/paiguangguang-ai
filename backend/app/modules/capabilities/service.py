from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.capabilities.models import (
    CapabilityDefinition,
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
from app.modules.observability.models import AuditEvent
from app.repositories import utc_now

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


def public_view(definition: CapabilityDefinition, version: CapabilityVersion) -> PublicCapability:
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

    def detail(self, capability_id: str) -> CapabilityDetail:
        return detail_view(self._get(capability_id))

    def create(
        self, payload: CapabilityCreate, *, actor_id: str
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
            source="admin",
            created_by=actor_id,
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
        draft = next(
            (item for item in definition.versions if version_id and item.id == version_id),
            None,
        ) or latest_draft(definition.versions)
        if draft is None or draft.status != "draft":
            raise HTTPException(status_code=409, detail="No editable draft to publish")
        snapshot = CapabilitySnapshot.model_validate(loads(draft.snapshot_json, {}))
        if not snapshot.name.strip():
            raise HTTPException(status_code=422, detail="Capability name is required")
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
        return detail_view(self._get(capability_id))

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
        return detail_view(self._get(capability_id))

    def public_list(self, *, kind: str | None = None, query: str = "") -> list[PublicCapability]:
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
        for definition in self.session.scalars(
            statement.order_by(CapabilityDefinition.updated_at.desc())
        ):
            version = latest_published(definition.versions)
            if version is not None:
                result.append(public_view(definition, version))
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
