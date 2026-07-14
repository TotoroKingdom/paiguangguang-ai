from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from dotenv import load_dotenv
from sqlalchemy import func, select

from app.core.config import Settings, get_settings
from app.db.alembic import get_alembic_config
from app.db.bootstrap import initialize_database
from app.db.models import Permission, Role, User, Workspace
from app.db.session import build_engine, build_session_factory
from app.services.auth import AuthService, password_context


def verify_database(settings: Settings) -> dict[str, object]:
    initialize_database(settings)
    initialize_database(settings)
    engine = build_engine(settings)
    alembic_config = get_alembic_config(settings)
    expected_heads = tuple(ScriptDirectory.from_config(alembic_config).get_heads())
    with engine.connect() as connection:
        current_heads = tuple(MigrationContext.configure(connection).get_current_heads())
    if current_heads != expected_heads:
        raise RuntimeError(f"Database migration mismatch: current={current_heads}, expected={expected_heads}")

    session_factory = build_session_factory(settings, engine=engine)
    with session_factory() as session:
        admin = session.scalar(select(User).where(User.email == settings.admin_user_email.strip().lower()))
        if admin is None or not admin.is_active:
            raise RuntimeError("Configured administrator is missing or inactive")
        default_workspace = session.scalar(select(Workspace).where(Workspace.slug == "default"))
        if default_workspace is None or not default_workspace.is_default:
            raise RuntimeError("Default workspace is not initialized")
        if not any(role.name == "system_admin" for role in admin.roles):
            raise RuntimeError("Configured administrator does not have system_admin")
        if not any(item.workspace_id == default_workspace.id for item in admin.workspace_memberships):
            raise RuntimeError("Configured administrator is not in the default workspace")
        if not AuthService(settings).verify_password(settings.admin_user_password, admin.hashed_password):
            raise RuntimeError("Configured administrator password verification failed")
        password_scheme = password_context.identify(admin.hashed_password)
        if password_scheme != "pbkdf2_sha256":
            raise RuntimeError("Configured administrator password is not PBKDF2-SHA256")
        return {
            "migration_heads": list(current_heads),
            "users": session.scalar(select(func.count()).select_from(User)),
            "roles": session.scalar(select(func.count()).select_from(Role)),
            "permissions": session.scalar(select(func.count()).select_from(Permission)),
            "workspaces": session.scalar(select(func.count()).select_from(Workspace)),
            "admin_active": admin.is_active,
            "admin_has_system_admin": True,
            "admin_in_default_workspace": True,
            "password_scheme": password_scheme,
            "idempotency_passes": 2,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize and verify the configured application database")
    parser.add_argument("--env-file", type=Path, default=Path("dev.env"))
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)
    report = verify_database(get_settings())
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
