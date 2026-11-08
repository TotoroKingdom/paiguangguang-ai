import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import APIError
from app.core.security import (
    hash_token,
    hash_user_password,
    hmac_digest,
    new_secret,
    verify_password,
)
from app.modules.identity.models import (
    AccountSequence,
    AdminUser,
    AdminUserLink,
    AuthRateEvent,
    RegistrationIdempotency,
    User,
    UserRecoveryCode,
    UserSession,
)
from app.modules.identity.schemas import (
    RegisterRequest,
    RecoveryMaterial,
    UserView,
)
from app.modules.observability.service import record_audit
from app.repositories import utc_now

ACCOUNT_SEQUENCE_NAME = "user_account"
FIRST_USER_ACCOUNT = 100
BOOTSTRAP_ADMIN_ACCOUNT = "1"
ACCOUNT_PATTERN = re.compile(r"^[1-9][0-9]*$")
WEAK_PASSWORDS = {
    "123456",
    "1234567",
    "12345678",
    "123456789",
    "1234567890",
    "111111",
    "000000",
    "654321",
    "abcdef",
    "qwerty",
    "password",
    "passw0rd",
    "admin123",
    "letmein",
    "iloveyou",
    "123123",
    "666666",
    "888888",
}
DUMMY_PASSWORD_HASH = hash_user_password(new_secret(24))


@dataclass
class UserPrincipal:
    user: User
    session: UserSession

    @property
    def scope(self) -> str:
        return self.session.scope

    @property
    def is_active(self) -> bool:
        return self.user.status == "ACTIVE"

    @property
    def is_admin(self) -> bool:
        return self.user.role == "ADMIN"

    @property
    def is_creator(self) -> bool:
        return self.user.role in {"CREATOR", "ADMIN"}


@dataclass
class IssuedSession:
    principal: UserPrincipal
    token: str
    csrf_token: str


def aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc)


def normalize_account(value: str) -> str:
    account = value.strip()
    if not ACCOUNT_PATTERN.match(account):
        raise APIError(422, "ACCOUNT_NUMBER_INVALID", "账号格式不正确")
    return account


def ensure_account_integer_capacity(account: str) -> None:
    if len(account) > 30:
        raise APIError(503, "ACCOUNT_CAPACITY_EXHAUSTED", "账号序列达到当前技术容量")


def validate_user_password(
    password: str,
    *,
    confirm: str | None = None,
    account_number: str | None = None,
    nickname: str | None = None,
) -> None:
    minimum = settings.user_password_min_length
    if len(password) < minimum:
        raise APIError(422, "PASSWORD_TOO_SHORT", f"密码至少需要 {minimum} 位")
    if len(password) > 128:
        raise APIError(422, "PASSWORD_TOO_WEAK", "密码不能超过 128 位")
    if confirm is not None and password != confirm:
        raise APIError(422, "PASSWORD_MISMATCH", "两次输入的密码不一致")
    if password.lower() in WEAK_PASSWORDS:
        raise APIError(422, "PASSWORD_TOO_WEAK", "密码过于常见，请更换")
    if len(set(password)) == 1:
        raise APIError(422, "PASSWORD_TOO_WEAK", "密码不能是重复字符")
    if password in "0123456789abcdefghijklmnopqrstuvwxyz":
        raise APIError(422, "PASSWORD_TOO_WEAK", "密码不能是连续字符")
    if account_number and password == account_number:
        raise APIError(422, "PASSWORD_TOO_WEAK", "密码不能与账号相同")
    if nickname and password == nickname:
        raise APIError(422, "PASSWORD_TOO_WEAK", "密码不能与昵称相同")


def new_recovery_code() -> str:
    raw = new_secret(32).replace("-", "").replace("_", "").upper()
    groups = [raw[index : index + 8] for index in range(0, 32, 8)]
    return "PGG-" + "-".join(groups)


def recovery_hash(code: str) -> str:
    return hmac_digest(settings.recovery_secret, code.strip().upper())


def user_view(user: User) -> UserView:
    return UserView(
        id=user.id,
        accountNumber=user.account_number,
        nickname=user.nickname,
        role=user.role,
        status=user.status,
        version=user.version,
        createdAt=user.created_at.replace(tzinfo=timezone.utc),
        activatedAt=aware(user.activated_at),
        lastLoginAt=aware(user.last_login_at),
    )


class DbRateLimiter:
    """Database-backed limiter shared across processes and workers."""

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _bucket(value: str) -> str:
        return hmac_digest(settings.recovery_secret, value)

    def ensure(self, action: str, bucket_raw: str, *, limit: int, window_seconds: int) -> None:
        now = utc_now()
        bucket = self._bucket(bucket_raw)
        since = now - timedelta(seconds=window_seconds)
        self.session.execute(
            delete(AuthRateEvent).where(AuthRateEvent.created_at < now - timedelta(days=2))
        )
        count = self.session.scalar(
            select(func.count(AuthRateEvent.id)).where(
                AuthRateEvent.action == action,
                AuthRateEvent.bucket == bucket,
                AuthRateEvent.created_at >= since,
            )
        )
        if (count or 0) >= limit:
            raise APIError(
                429,
                "RATE_LIMITED",
                "请求过于频繁，请稍后再试",
                retry_after_seconds=window_seconds,
            )
        self.session.add(AuthRateEvent(action=action, bucket=bucket, created_at=now))

    def allow(self, action: str, bucket_raw: str, *, limit: int, window_seconds: int) -> bool:
        now = utc_now()
        bucket = self._bucket(bucket_raw)
        count = self.session.scalar(
            select(func.count(AuthRateEvent.id)).where(
                AuthRateEvent.action == action,
                AuthRateEvent.bucket == bucket,
                AuthRateEvent.created_at >= now - timedelta(seconds=window_seconds),
            )
        )
        return (count or 0) < limit

    def check(self, action: str, bucket_raw: str, *, limit: int, window_seconds: int) -> None:
        if not self.allow(action, bucket_raw, limit=limit, window_seconds=window_seconds):
            raise APIError(
                429,
                "RATE_LIMITED",
                "请求过于频繁，请稍后再试",
                retry_after_seconds=window_seconds,
            )

    def record(self, action: str, bucket_raw: str) -> None:
        self.session.add(
            AuthRateEvent(action=action, bucket=self._bucket(bucket_raw), created_at=utc_now())
        )


class UserIdentityService:
    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------------ register
    def register(
        self,
        payload: RegisterRequest,
        *,
        idempotency_key: str,
        client_ip: str,
    ) -> tuple[dict[str, Any], str | None]:
        if not settings.registration_enabled:
            raise APIError(503, "REGISTRATION_DISABLED", "注册暂未开放")
        key = (idempotency_key or "").strip()
        if len(key) < 16 or len(key) > 200:
            raise APIError(422, "VALIDATION_ERROR", "缺少有效的 Idempotency-Key")
        validate_user_password(
            payload.password, confirm=payload.passwordConfirm, nickname=payload.nickname or None
        )
        request_hash = hashlib.sha256(
            json.dumps(
                {
                    "password": payload.password,
                    "nickname": payload.nickname,
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        key_hash = hash_token(key)
        ip = (client_ip or "unknown").strip().lower()

        self.session.execute(text("BEGIN IMMEDIATE"))
        try:
            limiter = DbRateLimiter(self.session)
            limiter.ensure(
                "register_ip_hour",
                ip,
                limit=settings.register_rate_per_hour,
                window_seconds=3600,
            )
            limiter.ensure(
                "register_ip_day",
                ip,
                limit=settings.register_rate_per_day,
                window_seconds=86400,
            )
            existing = self.session.scalar(
                select(RegistrationIdempotency).where(
                    RegistrationIdempotency.key_hash == key_hash
                )
            )
            if existing is not None:
                if existing.request_hash != request_hash:
                    raise APIError(409, "IDEMPOTENCY_CONFLICT", "幂等键已用于其他请求")
                data = json.loads(existing.response_json)
                data["replayed"] = True
                self.session.commit()
                return data, None

            sequence = self.session.get(AccountSequence, ACCOUNT_SEQUENCE_NAME)
            if sequence is None:
                sequence = AccountSequence(
                    name=ACCOUNT_SEQUENCE_NAME,
                    next_account_number=str(FIRST_USER_ACCOUNT),
                    updated_at=utc_now(),
                )
                self.session.add(sequence)
                self.session.flush()
            account_number = sequence.next_account_number
            ensure_account_integer_capacity(account_number)
            sequence.next_account_number = str(int(account_number) + 1)
            sequence.updated_at = utc_now()
            self.session.flush()

            now = utc_now()
            user = User(
                account_number=account_number,
                password_hash=hash_user_password(payload.password),
                nickname=payload.nickname,
                role="USER",
                status="PENDING",
                version=1,
                authz_version=1,
                created_at=now,
                updated_at=now,
            )
            self.session.add(user)
            self.session.flush()
            code = self._issue_recovery_code(user)
            view = user_view(user).model_dump(mode="json")
            response = {
                "user": view,
                "recovery": None,
                "sessionIssued": False,
                "replayed": False,
            }
            self.session.add(
                RegistrationIdempotency(
                    key_hash=key_hash,
                    request_hash=request_hash,
                    user_id=user.id,
                    response_json=json.dumps(response, ensure_ascii=False),
                    created_at=now,
                )
            )
            record_audit(
                self.session,
                actor_type="user",
                actor_id=user.id,
                action="auth.register",
                resource_type="user",
                resource_id=user.id,
                client_ip=client_ip,
            )
            self.session.commit()
            return response, code
        except IntegrityError:
            self.session.rollback()
            raise APIError(409, "STATE_CONFLICT", "注册冲突，请重试")
        except Exception:
            self.session.rollback()
            raise

    # --------------------------------------------------------------------- login
    def login(
        self,
        account_number: str,
        password: str,
        *,
        client_ip: str,
        user_agent: str,
    ) -> IssuedSession:
        account = account_number.strip()
        ip = (client_ip or "unknown").strip().lower()
        limiter = DbRateLimiter(self.session)
        limiter.check(
            "login_failure",
            f"{account}:{ip}",
            limit=settings.login_rate_per_window,
            window_seconds=settings.login_rate_window_seconds,
        )
        limiter.check(
            "login_ip_failure",
            ip,
            limit=settings.login_ip_rate_per_window,
            window_seconds=settings.login_rate_window_seconds,
        )
        user = None
        if ACCOUNT_PATTERN.match(account):
            user = self.session.scalar(select(User).where(User.account_number == account))
        encoded = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        valid = verify_password(password, encoded)
        if user is None or not valid or user.status == "REJECTED":
            self._record_login_failure(limiter, account, ip)
            self.session.commit()
            raise APIError(401, "AUTH_INVALID_CREDENTIALS", "账号或密码错误")
        if user.status == "DISABLED":
            self._record_login_failure(limiter, account, ip)
            self.session.commit()
            raise APIError(403, "ACCOUNT_NOT_ACTIVE", "账号已停用，请联系管理员")

        scope = "FULL" if user.status == "ACTIVE" else "STATUS_ONLY"
        now = utc_now()
        lifetime = (
            settings.user_session_max_age_seconds
            if scope == "FULL"
            else settings.status_session_max_age_seconds
        )
        token = new_secret(32)
        csrf_token = new_secret(24)
        user_session = UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            csrf_hash=hash_token(csrf_token),
            scope=scope,
            authz_version=user.authz_version,
            created_at=now,
            expires_at=now + timedelta(seconds=lifetime),
            last_seen_at=now,
            client_ip=(client_ip or "")[:64],
            user_agent=(user_agent or "")[:255],
        )
        user.last_login_at = now
        user.updated_at = now
        self.session.add(user_session)
        self.session.execute(
            delete(UserSession).where(
                UserSession.expires_at < now, UserSession.user_id == user.id
            )
        )
        record_audit(
            self.session,
            actor_type="user",
            actor_id=user.id,
            action="auth.login",
            resource_type="user_session",
            resource_id=user_session.id,
            client_ip=client_ip,
        )
        self.session.commit()
        return IssuedSession(
            principal=UserPrincipal(user=user, session=user_session),
            token=token,
            csrf_token=csrf_token,
        )

    def _record_login_failure(
        self, limiter: DbRateLimiter, account: str, ip: str
    ) -> None:
        limiter.record("login_failure", f"{account}:{ip}")
        limiter.record("login_ip_failure", ip)

    # ------------------------------------------------------------------- session
    def resolve_session(self, token: str | None) -> UserPrincipal | None:
        if not token:
            return None
        now = utc_now()
        row = self.session.execute(
            select(UserSession, User)
            .join(User, User.id == UserSession.user_id)
            .where(
                UserSession.token_hash == hash_token(token),
                UserSession.expires_at > now,
                UserSession.revoked_at.is_(None),
            )
        ).first()
        if row is None:
            return None
        user_session, user = row
        if user_session.authz_version != user.authz_version:
            return None
        if user.status == "ACTIVE" and user_session.scope == "STATUS_ONLY":
            user_session.scope = "FULL"
            user_session.expires_at = now + timedelta(
                seconds=settings.user_session_max_age_seconds
            )
            self.session.commit()
        if user_session.last_seen_at < now - timedelta(minutes=5):
            user_session.last_seen_at = now
            self.session.commit()
        return UserPrincipal(user=user, session=user_session)

    def logout(self, principal: UserPrincipal, *, client_ip: str = "") -> None:
        principal.session.revoked_at = utc_now()
        record_audit(
            self.session,
            actor_type="user",
            actor_id=principal.user.id,
            action="auth.logout",
            resource_type="user_session",
            resource_id=principal.session.id,
            client_ip=client_ip,
        )
        self.session.commit()

    def revoke_sessions(self, user_id: str, *, except_session_id: str | None = None) -> int:
        now = utc_now()
        statement = select(UserSession).where(
            UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
        )
        if except_session_id:
            statement = statement.where(UserSession.id != except_session_id)
        count = 0
        for item in self.session.scalars(statement):
            item.revoked_at = now
            count += 1
        return count

    # ------------------------------------------------------------------ recovery
    def _issue_recovery_code(self, user: User) -> str:
        now = utc_now()
        for existing in self.session.scalars(
            select(UserRecoveryCode).where(
                UserRecoveryCode.user_id == user.id, UserRecoveryCode.used_at.is_(None)
            )
        ):
            existing.revoked_at = now
        code = new_recovery_code()
        self.session.add(
            UserRecoveryCode(user_id=user.id, code_hash=recovery_hash(code), issued_at=now)
        )
        self.session.flush()
        return code

    def complete_recovery(
        self,
        account_number: str,
        code: str,
        new_password: str,
        confirm: str,
        *,
        client_ip: str,
    ) -> str:
        account = account_number.strip()
        ip = (client_ip or "unknown").strip().lower()
        limiter = DbRateLimiter(self.session)
        limiter.check(
            "recovery_failure_hour",
            f"{account}:{ip}",
            limit=settings.recovery_rate_per_hour,
            window_seconds=3600,
        )
        limiter.check(
            "recovery_failure_day",
            ip,
            limit=settings.recovery_rate_per_day,
            window_seconds=86400,
        )
        user = (
            self.session.scalar(select(User).where(User.account_number == account))
            if ACCOUNT_PATTERN.match(account)
            else None
        )
        if user is None or user.status == "REJECTED":
            self._record_recovery_failure(limiter, account, ip)
            self.session.commit()
            raise APIError(401, "RECOVERY_INVALID", "账号或恢复码无效")
        digest = recovery_hash(code)
        record = self.session.scalar(
            select(UserRecoveryCode).where(
                UserRecoveryCode.user_id == user.id,
                UserRecoveryCode.code_hash == digest,
                UserRecoveryCode.used_at.is_(None),
                UserRecoveryCode.revoked_at.is_(None),
            )
        )
        if record is None:
            self._record_recovery_failure(limiter, account, ip)
            self.session.commit()
            raise APIError(401, "RECOVERY_INVALID", "账号或恢复码无效")
        validate_user_password(new_password, confirm=confirm, account_number=user.account_number)
        now = utc_now()
        user.password_hash = hash_user_password(new_password)
        user.authz_version += 1
        user.version += 1
        user.updated_at = now
        record.used_at = now
        self.revoke_sessions(user.id)
        new_code = self._issue_recovery_code(user)
        record_audit(
            self.session,
            actor_type="user",
            actor_id=user.id,
            action="auth.recovery.complete",
            resource_type="user",
            resource_id=user.id,
            client_ip=client_ip,
        )
        self.session.commit()
        return new_code

    def _record_recovery_failure(
        self, limiter: DbRateLimiter, account: str, ip: str
    ) -> None:
        limiter.record("recovery_failure_hour", f"{account}:{ip}")
        limiter.record("recovery_failure_day", ip)

    def rotate_recovery_code(self, principal: UserPrincipal, current_password: str) -> str:
        if not verify_password(current_password, principal.user.password_hash):
            raise APIError(401, "AUTH_INVALID_CREDENTIALS", "当前密码错误")
        code = self._issue_recovery_code(principal.user)
        record_audit(
            self.session,
            actor_type="user",
            actor_id=principal.user.id,
            action="auth.recovery.rotate",
            resource_type="user",
            resource_id=principal.user.id,
        )
        self.session.commit()
        return code

    def change_password(
        self,
        principal: UserPrincipal,
        current_password: str,
        new_password: str,
        confirm: str,
    ) -> str:
        if not verify_password(current_password, principal.user.password_hash):
            raise APIError(401, "AUTH_INVALID_CREDENTIALS", "当前密码错误")
        validate_user_password(
            new_password,
            confirm=confirm,
            account_number=principal.user.account_number,
            nickname=principal.user.nickname or None,
        )
        now = utc_now()
        principal.user.password_hash = hash_user_password(new_password)
        principal.user.authz_version += 1
        principal.user.version += 1
        principal.user.updated_at = now
        self.revoke_sessions(principal.user.id, except_session_id=principal.session.id)
        principal.session.authz_version = principal.user.authz_version
        code = self._issue_recovery_code(principal.user)
        record_audit(
            self.session,
            actor_type="user",
            actor_id=principal.user.id,
            action="auth.password.change",
            resource_type="user",
            resource_id=principal.user.id,
        )
        self.session.commit()
        return code

    # -------------------------------------------------------------------- admin
    def ensure_unified_admin(self) -> None:
        """One-time mapping from legacy admin_users to unified users."""
        legacy_admins = list(
            self.session.scalars(
                select(AdminUser)
                .where(AdminUser.role == "admin", AdminUser.is_active.is_(True))
                .order_by(AdminUser.created_at)
            )
        )
        changed = False
        for legacy in legacy_admins:
            if self.session.scalar(
                select(AdminUserLink).where(AdminUserLink.legacy_admin_id == legacy.id)
            ):
                continue
            account = BOOTSTRAP_ADMIN_ACCOUNT
            if self.session.scalar(select(User).where(User.account_number == account)):
                account = self._next_account_number()
            now = utc_now()
            user = User(
                account_number=account,
                password_hash=legacy.password_hash,
                nickname=legacy.username,
                role="ADMIN",
                status="ACTIVE",
                version=1,
                authz_version=1,
                created_at=now,
                updated_at=now,
                activated_at=now,
            )
            self.session.add(user)
            self.session.flush()
            self.session.add(
                AdminUserLink(
                    legacy_admin_id=legacy.id,
                    user_id=user.id,
                    migrated_at=now,
                    migration_source="legacy_admin_bootstrap",
                )
            )
            changed = True
        if changed:
            self.session.commit()

    def _next_account_number(self) -> str:
        sequence = self.session.get(AccountSequence, ACCOUNT_SEQUENCE_NAME)
        if sequence is None:
            sequence = AccountSequence(
                name=ACCOUNT_SEQUENCE_NAME,
                next_account_number=str(FIRST_USER_ACCOUNT),
                updated_at=utc_now(),
            )
            self.session.add(sequence)
            self.session.flush()
        account = sequence.next_account_number
        sequence.next_account_number = str(int(account) + 1)
        sequence.updated_at = utc_now()
        self.session.flush()
        return account

    def list_users(
        self,
        *,
        status: str | None = None,
        role: str | None = None,
        query: str = "",
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[User], int, str | None]:
        statement = select(User)
        count_statement = select(func.count(User.id))
        conditions = []
        if status:
            conditions.append(User.status == status)
        if role:
            conditions.append(User.role == role)
        if query.strip():
            value = f"%{query.strip()}%"
            conditions.append(
                User.account_number.ilike(value) | User.nickname.ilike(value)
            )
        for condition in conditions:
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)
        if cursor:
            try:
                created_raw, user_id = cursor.split(":", 1)
                created = datetime.fromisoformat(created_raw)
            except ValueError:
                raise APIError(422, "VALIDATION_ERROR", "分页游标无效")
            statement = statement.where(
                (User.created_at < created)
                | ((User.created_at == created) & (User.id < user_id))
            )
        total = self.session.scalar(count_statement) or 0
        users = list(
            self.session.scalars(
                statement.order_by(User.created_at.desc(), User.id.desc()).limit(limit + 1)
            )
        )
        next_cursor = None
        if len(users) > limit:
            last = users[limit - 1]
            next_cursor = f"{last.created_at.isoformat()}:{last.id}"
        return users[:limit], total, next_cursor

    def get_user(self, user_id: str) -> User:
        user = self.session.get(User, user_id)
        if user is None:
            raise APIError(404, "NOT_FOUND", "用户不存在")
        return user

    def _active_admin_count(self, *, excluding: str | None = None) -> int:
        statement = select(func.count(User.id)).where(
            User.role == "ADMIN", User.status == "ACTIVE"
        )
        if excluding:
            statement = statement.where(User.id != excluding)
        return self.session.scalar(statement) or 0

    def _check_admin_target(self, user: User, *, removing_admin: bool) -> None:
        if user.role == "ADMIN" and user.status == "ACTIVE" and removing_admin:
            if self._active_admin_count(excluding=user.id) == 0:
                raise APIError(409, "LAST_ADMIN_PROTECTED", "不能停用或降级最后一个有效管理员")

    def moderate(
        self,
        user_id: str,
        action: str,
        *,
        expected_version: int,
        reason: str,
        actor_id: str,
        client_ip: str,
    ) -> tuple[User, str]:
        user = self.get_user(user_id)
        if user.version != expected_version:
            raise APIError(409, "STATE_CONFLICT", "用户状态已被其他管理员修改")
        now = utc_now()
        if action == "activate":
            if user.status not in {"PENDING", "DISABLED"}:
                raise APIError(409, "STATE_CONFLICT", "当前状态不能激活")
            user.status = "ACTIVE"
            user.activated_at = now
            user.disabled_at = None
            user.status_reason = ""
        elif action == "reject":
            if user.status != "PENDING":
                raise APIError(409, "STATE_CONFLICT", "只有待审核用户可以拒绝")
            if not reason.strip():
                raise APIError(422, "VALIDATION_ERROR", "拒绝原因不能为空")
            user.status = "REJECTED"
            user.status_reason = reason.strip()
        elif action == "disable":
            if user.status != "ACTIVE":
                raise APIError(409, "STATE_CONFLICT", "只有已激活用户可以停用")
            if not reason.strip():
                raise APIError(422, "VALIDATION_ERROR", "停用原因不能为空")
            self._check_admin_target(user, removing_admin=True)
            user.status = "DISABLED"
            user.disabled_at = now
            user.status_reason = reason.strip()
            user.authz_version += 1
            self.revoke_sessions(user.id)
        elif action == "restore":
            if user.status != "DISABLED":
                raise APIError(409, "STATE_CONFLICT", "只有已停用用户可以恢复")
            user.status = "ACTIVE"
            user.disabled_at = None
            user.status_reason = ""
        else:
            raise APIError(400, "BAD_REQUEST", "未知操作")
        user.version += 1
        user.updated_at = now
        audit = record_audit(
            self.session,
            actor_type="user",
            actor_id=actor_id,
            action=f"admin.user.{action}",
            resource_type="user",
            resource_id=user.id,
            client_ip=client_ip,
            detail={"reason": reason.strip()},
        )
        self.session.commit()
        return user, audit.id

    def set_role(
        self,
        user_id: str,
        role: str,
        *,
        expected_version: int,
        reason: str,
        actor_id: str,
        client_ip: str,
    ) -> tuple[User, str]:
        user = self.get_user(user_id)
        if user.version != expected_version:
            raise APIError(409, "STATE_CONFLICT", "用户状态已被其他管理员修改")
        if role not in {"USER", "CREATOR", "ADMIN"}:
            raise APIError(422, "VALIDATION_ERROR", "角色不合法")
        if user.id == actor_id and role != "ADMIN":
            raise APIError(409, "STATE_CONFLICT", "管理员不能移除自己的管理员角色")
        self._check_admin_target(user, removing_admin=role != "ADMIN")
        user.role = role
        user.version += 1
        user.authz_version += 1
        user.updated_at = utc_now()
        self.revoke_sessions(user.id)
        audit = record_audit(
            self.session,
            actor_type="user",
            actor_id=actor_id,
            action="admin.user.role",
            resource_type="user",
            resource_id=user.id,
            client_ip=client_ip,
            detail={"role": role, "reason": reason.strip()},
        )
        self.session.commit()
        return user, audit.id
