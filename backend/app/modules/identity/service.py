import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_password, hash_token, new_secret, verify_password
from app.modules.identity.models import AdminSession, AdminUser, User
from app.repositories import utc_now

logger = logging.getLogger(__name__)


@dataclass
class AdminPrincipal:
    user: AdminUser
    session: AdminSession


@dataclass
class CreatedSession:
    principal: AdminPrincipal
    token: str
    csrf_token: str


class LoginLimiter:
    """Small in-process limiter suitable for the current single-instance deployment."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._failures: dict[str, list[float]] = {}
        self._locked_until: dict[str, float] = {}

    def _prune(self, key: str, now: float) -> None:
        cutoff = now - settings.admin_login_window_seconds
        values = [stamp for stamp in self._failures.get(key, []) if stamp >= cutoff]
        if values:
            self._failures[key] = values
        else:
            self._failures.pop(key, None)

    def ensure_allowed(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            locked_until = self._locked_until.get(key, 0)
            if locked_until > now:
                raise HTTPException(
                    status_code=423,
                    detail="Too many login attempts. Try again later.",
                )
            self._locked_until.pop(key, None)
            self._prune(key, now)

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            values = self._failures.setdefault(key, [])
            values.append(now)
            if len(values) >= settings.admin_login_max_attempts:
                self._locked_until[key] = now + settings.admin_login_lock_seconds
                self._failures.pop(key, None)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)


login_limiter = LoginLimiter()


class AdminIdentityService:
    def __init__(self, session: Session):
        self.session = session

    def ensure_bootstrap_admin(self) -> None:
        if settings.admin_password is None:
            return
        password = settings.admin_password.get_secret_value()
        if not password:
            return
        if len(password) < 12:
            raise RuntimeError("ASSISTANT_ADMIN_PASSWORD must contain at least 12 characters")
        username = settings.admin_username.strip()
        if not username:
            raise RuntimeError("ASSISTANT_ADMIN_USERNAME must not be blank")
        encoded = hash_password(password)
        user = self.session.scalar(select(AdminUser).where(AdminUser.username == username))
        now = utc_now()
        if user is None:
            self.session.add(
                AdminUser(
                    username=username,
                    password_hash=encoded,
                    role="admin",
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
        self.session.commit()

    def has_active_admin(self) -> bool:
        legacy = (
            self.session.scalar(
                select(AdminUser.id).where(
                    AdminUser.is_active.is_(True), AdminUser.role == "admin"
                )
            )
            is not None
        )
        unified = (
            self.session.scalar(
                select(User.id).where(User.status == "ACTIVE", User.role == "ADMIN")
            )
            is not None
        )
        return legacy or unified

    def login(
        self,
        username: str,
        password: str,
        *,
        client_ip: str,
        user_agent: str,
    ) -> CreatedSession:
        key = f"{client_ip.strip().lower()}:{username.strip().lower()}"
        login_limiter.ensure_allowed(key)
        user = self.session.scalar(
            select(AdminUser).where(AdminUser.username == username.strip())
        )
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            login_limiter.record_failure(key)
            raise HTTPException(status_code=401, detail="Invalid administrator credentials")
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Administrator permission required")

        login_limiter.reset(key)
        now = utc_now()
        expires_at = now + timedelta(seconds=settings.admin_session_max_age_seconds)
        token = new_secret()
        csrf_token = new_secret(24)
        admin_session = AdminSession(
            user_id=user.id,
            token_hash=hash_token(token),
            csrf_hash=hash_token(csrf_token),
            created_at=now,
            expires_at=expires_at,
            last_seen_at=now,
            client_ip=client_ip[:64],
            user_agent=user_agent[:255],
        )
        user.last_login_at = now
        user.updated_at = now
        self.session.add(admin_session)
        self.session.execute(
            delete(AdminSession).where(
                AdminSession.expires_at < now,
                AdminSession.user_id == user.id,
            )
        )
        self.session.flush()
        return CreatedSession(
            principal=AdminPrincipal(user=user, session=admin_session),
            token=token,
            csrf_token=csrf_token,
        )

    def resolve(self, token: str | None) -> AdminPrincipal | None:
        if not token:
            return None
        now = utc_now()
        row = self.session.execute(
            select(AdminSession, AdminUser)
            .join(AdminUser, AdminUser.id == AdminSession.user_id)
            .where(
                AdminSession.token_hash == hash_token(token),
                AdminSession.expires_at > now,
                AdminUser.is_active.is_(True),
            )
        ).first()
        if row is None:
            return None
        admin_session, user = row
        if admin_session.last_seen_at < now - timedelta(minutes=5):
            admin_session.last_seen_at = now
            self.session.commit()
        return AdminPrincipal(user=user, session=admin_session)

    def logout(self, principal: AdminPrincipal) -> None:
        self.session.delete(principal.session)
        self.session.commit()
