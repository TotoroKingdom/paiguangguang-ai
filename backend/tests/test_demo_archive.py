from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.main import app
from app.modules.capabilities.models import CapabilityDefinition, CapabilityVersion
from app.modules.capabilities.service import CapabilityService
from app.modules.observability.models import AuditEvent
from app.repositories import utc_now


def test_demo_catalog_archive_is_idempotent_and_preserves_history():
    with SessionLocal() as session:
        demo_definitions = list(
            session.scalars(
                select(CapabilityDefinition).where(
                    CapabilityDefinition.source == "demo"
                )
            )
        )
        assert demo_definitions
        demo_ids = {item.id for item in demo_definitions}
        demo_versions = {
            item.id: list(
                session.scalars(
                    select(CapabilityVersion.id).where(
                        CapabilityVersion.capability_id == item.id
                    )
                )
            )
            for item in demo_definitions
        }
        now = utc_now()
        managed = CapabilityDefinition(
            slug="managed-archive-control",
            kind="tool",
            name="真实能力",
            description="",
            category="系统",
            icon="spark",
            status="published",
            source="admin",
            created_by="admin",
            created_at=now,
            updated_at=now,
        )
        session.add(managed)
        session.commit()
        managed_id = managed.id

        archived = CapabilityService(session).archive_existing_demo_catalog()
        assert set(archived) == demo_ids
        session.expire_all()
        for definition in demo_definitions:
            refreshed = session.get(CapabilityDefinition, definition.id)
            assert refreshed.status == "disabled"
            assert list(
                session.scalars(
                    select(CapabilityVersion.id).where(
                        CapabilityVersion.capability_id == definition.id
                    )
                )
            ) == demo_versions[definition.id]
        assert session.get(CapabilityDefinition, managed_id).status == "published"

        audits = list(
            session.scalars(
                select(AuditEvent).where(AuditEvent.action == "capability.demo.archived")
            )
        )
        assert {item.resource_id for item in audits} == demo_ids

        assert CapabilityService(session).archive_existing_demo_catalog() == []
        assert (
            session.scalar(
                select(AuditEvent.id)
                .where(AuditEvent.action == "capability.demo.archived")
                .offset(len(demo_ids))
            )
            is None
        )


def test_disabled_demo_catalog_is_archived_during_application_startup(monkeypatch):
    monkeypatch.setattr(settings, "demo_catalog_enabled", False)
    with TestClient(app) as client:
        assert client.get("/api/v1/capabilities").json()["items"] == []
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(CapabilityDefinition.id).where(
                    CapabilityDefinition.source == "demo",
                    CapabilityDefinition.status != "disabled",
                )
            )
            is None
        )
