import base64
import hashlib
import json
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import APIError
from app.modules.personal.models import McpConnection, McpServer, PersonalSkill, UserFile
from app.modules.personal.storage import storage_lock
from app.repositories import utc_now

MAX_FILE_BYTES = 5 * 1024 * 1024
SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
SUPPORTED_TEXT_CONTENT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    # Some browsers send Markdown files as the generic binary MIME type. The
    # extension and UTF-8/NUL checks below still gate this compatibility path.
    "application/octet-stream",
}


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.encryption_secret.encode("utf-8")).digest()
    )
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as error:
        raise APIError(500, "CREDENTIAL_UNREADABLE", "凭据无法解密") from error


def clean_filename(value: str) -> str:
    name = Path(value or "").name.strip()
    if not name or name in {".", ".."} or any(ord(char) < 32 for char in name):
        raise APIError(422, "FILE_NAME_INVALID", "文件名不合法")
    if len(name) > 200:
        raise APIError(422, "FILE_NAME_INVALID", "文件名过长")
    return name


class PersonalService:
    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------------- skills
    def list_skills(self, user_id: str) -> list[PersonalSkill]:
        return list(
            self.session.scalars(
                select(PersonalSkill)
                .where(PersonalSkill.user_id == user_id)
                .order_by(PersonalSkill.updated_at.desc())
            )
        )

    def get_skill(self, user_id: str, skill_id: str) -> PersonalSkill:
        skill = self.session.scalar(
            select(PersonalSkill).where(
                PersonalSkill.id == skill_id, PersonalSkill.user_id == user_id
            )
        )
        if skill is None:
            raise APIError(404, "NOT_FOUND", "Skill 不存在")
        return skill

    def create_skill(self, user_id: str, name: str, description: str, content: str) -> PersonalSkill:
        now = utc_now()
        skill = PersonalSkill(
            user_id=user_id,
            name=name.strip(),
            description=description.strip(),
            content_md=content,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self.session.add(skill)
        self.session.commit()
        return skill

    def update_skill(
        self, user_id: str, skill_id: str, name: str, description: str, content: str
    ) -> PersonalSkill:
        skill = self.get_skill(user_id, skill_id)
        skill.name = name.strip()
        skill.description = description.strip()
        skill.content_md = content
        skill.version += 1
        skill.updated_at = utc_now()
        self.session.commit()
        return skill

    def delete_skill(self, user_id: str, skill_id: str) -> None:
        skill = self.get_skill(user_id, skill_id)
        self.session.delete(skill)
        self.session.commit()

    # -------------------------------------------------------------------- files
    def list_files(self, user_id: str) -> list[UserFile]:
        return list(
            self.session.scalars(
                select(UserFile)
                .where(UserFile.user_id == user_id, UserFile.status == "active")
                .order_by(UserFile.created_at.desc())
            )
        )

    def get_file(self, user_id: str, file_id: str) -> UserFile:
        item = self.session.scalar(
            select(UserFile).where(
                UserFile.id == file_id,
                UserFile.user_id == user_id,
                UserFile.status == "active",
            )
        )
        if item is None:
            raise APIError(404, "NOT_FOUND", "文件不存在")
        return item

    def save_file(
        self, user_id: str, filename: str, content_type: str, data: bytes
    ) -> UserFile:
        if len(data) > MAX_FILE_BYTES:
            raise APIError(413, "FILE_TOO_LARGE", "文件超过 5 MiB")
        name = clean_filename(filename)
        extension = Path(name).suffix.lower()
        normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
        if (
            extension not in SUPPORTED_TEXT_EXTENSIONS
            or normalized_type not in SUPPORTED_TEXT_CONTENT_TYPES
        ):
            raise APIError(422, "FILE_TYPE_UNSUPPORTED", "仅支持 TXT 或 Markdown 文本文件")
        try:
            decoded = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise APIError(422, "FILE_CONTENT_INVALID", "文本文件必须使用 UTF-8 编码") from error
        if "\x00" in decoded:
            raise APIError(422, "FILE_CONTENT_INVALID", "文本文件内容无效")
        file_id = __import__("uuid").uuid4().hex
        root = Path(settings.storage_root).resolve()
        with storage_lock(root):
            directory = (root / user_id).resolve()
            if root not in directory.parents and directory != root:
                raise APIError(500, "STORAGE_INVALID", "文件存储路径异常")
            directory.mkdir(parents=True, exist_ok=True)
            target = directory / f"{file_id}.bin"
            target.write_bytes(data)
            now = utc_now()
            item = UserFile(
                id=file_id,
                user_id=user_id,
                filename=name,
                content_type=(content_type or "application/octet-stream")[:120],
                size_bytes=len(data),
                checksum=hashlib.sha256(data).hexdigest(),
                storage_path=str(target),
                status="active",
                created_at=now,
            )
            self.session.add(item)
            try:
                self.session.commit()
            except Exception:
                self.session.rollback()
                target.unlink(missing_ok=True)
                raise
            return item

    def read_file(self, user_id: str, file_id: str) -> tuple[UserFile, bytes]:
        item = self.get_file(user_id, file_id)
        path = Path(item.storage_path).resolve()
        root = Path(settings.storage_root).resolve()
        if root not in path.parents:
            raise APIError(500, "STORAGE_INVALID", "文件存储路径异常")
        if not path.exists():
            raise APIError(404, "NOT_FOUND", "文件内容不存在")
        return item, path.read_bytes()

    def read_file_prefix(self, user_id: str, file_id: str, limit: int) -> tuple[UserFile, bytes]:
        item = self.get_file(user_id, file_id)
        path = Path(item.storage_path).resolve()
        root = Path(settings.storage_root).resolve()
        if root not in path.parents:
            raise APIError(500, "STORAGE_INVALID", "文件存储路径异常")
        if not path.exists():
            raise APIError(404, "NOT_FOUND", "文件内容不存在")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise APIError(413, "FILE_TOO_LARGE", "文件超过 5 MiB")
        with path.open("rb") as source:
            return item, source.read(limit)

    def delete_file(self, user_id: str, file_id: str) -> None:
        with storage_lock(settings.storage_root):
            item = self.get_file(user_id, file_id)
            item.status = "deleted"
            item.deleted_at = utc_now()
            self.session.commit()

    # ---------------------------------------------------------------------- mcp
    def list_servers(self, *, approved_only: bool = True) -> list[McpServer]:
        from app.modules.runtime.mcp_client import MCP_TRANSPORT_STREAMABLE_HTTP

        statement = select(McpServer).order_by(McpServer.created_at.desc())
        if approved_only:
            statement = statement.where(
                McpServer.status == "approved",
                McpServer.transport == MCP_TRANSPORT_STREAMABLE_HTTP,
            )
        return list(self.session.scalars(statement))

    def get_server(self, server_id: str) -> McpServer:
        server = self.session.get(McpServer, server_id)
        if server is None:
            raise APIError(404, "NOT_FOUND", "MCP Server 不存在")
        return server

    def create_server(
        self,
        *,
        name: str,
        description: str,
        endpoint_url: str,
        transport: str,
        created_by: str,
        status: str = "pending",
    ) -> McpServer:
        from app.modules.runtime.mcp_client import (
            MCP_TRANSPORT_STREAMABLE_HTTP,
            validate_mcp_url,
        )

        now = utc_now()
        if transport != MCP_TRANSPORT_STREAMABLE_HTTP:
            raise APIError(
                422,
                "MCP_TRANSPORT_UNSUPPORTED",
                "MCP 仅支持 Streamable HTTP transport",
            )
        server = McpServer(
            name=name.strip(),
            description=description.strip(),
            endpoint_url=validate_mcp_url(endpoint_url),
            transport=transport,
            status=status,
            tools_json="[]",
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self.session.add(server)
        self.session.commit()
        return server

    def review_server(
        self, server_id: str, action: str, *, actor_id: str
    ) -> McpServer:
        server = self.get_server(server_id)
        if action not in {"approve", "disable"}:
            raise APIError(400, "BAD_REQUEST", "未知操作")
        server.status = "approved" if action == "approve" else "disabled"
        server.reviewed_by = actor_id
        server.reviewed_at = utc_now()
        server.updated_at = utc_now()
        self.session.commit()
        return server

    def list_connections(self, user_id: str) -> list[tuple[McpConnection, McpServer]]:
        return list(
            self.session.execute(
                select(McpConnection, McpServer)
                .join(McpServer, McpServer.id == McpConnection.server_id)
                .where(McpConnection.user_id == user_id)
                .order_by(McpConnection.created_at.desc())
            )
        )

    def connect_server(
        self, user_id: str, server_id: str, token: str
    ) -> McpConnection:
        from app.modules.runtime.mcp_client import MCP_TRANSPORT_STREAMABLE_HTTP

        server = self.get_server(server_id)
        if server.status != "approved":
            raise APIError(403, "MCP_SERVER_NOT_APPROVED", "只能连接平台已批准的 Server")
        if server.transport != MCP_TRANSPORT_STREAMABLE_HTTP:
            raise APIError(
                403,
                "MCP_TRANSPORT_UNSUPPORTED",
                "MCP 仅支持 Streamable HTTP transport",
            )
        connection = self.session.scalar(
            select(McpConnection).where(
                McpConnection.user_id == user_id,
                McpConnection.server_id == server.id,
            )
        )
        now = utc_now()
        if connection is None:
            connection = McpConnection(
                user_id=user_id,
                server_id=server.id,
                status="connected",
                created_at=now,
                updated_at=now,
            )
            self.session.add(connection)
        connection.status = "connected"
        connection.credential_ciphertext = encrypt_secret(token) if token else ""
        connection.credential_ref = ""
        connection.updated_at = now
        self.session.commit()
        return connection

    def delete_connection(self, user_id: str, connection_id: str) -> None:
        connection = self.session.scalar(
            select(McpConnection).where(
                McpConnection.id == connection_id, McpConnection.user_id == user_id
            )
        )
        if connection is None:
            raise APIError(404, "NOT_FOUND", "连接不存在")
        self.session.delete(connection)
        self.session.commit()
