from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.modules.capabilities.models import CapabilityDefinition
from app.modules.capabilities.service import CapabilityService

MAX_ARGUMENT_BYTES = 16 * 1024
MAX_RESULT_BYTES = 64 * 1024


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    side_effect: bool
    schema: dict[str, Any]
    handler: Callable[[Session, dict[str, Any], str], dict[str, Any]]


def _validate_value(name: str, value: Any, spec: dict[str, Any]) -> None:
    expected = spec.get("type")
    checks = {
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "array": lambda item: isinstance(item, list),
        "object": lambda item: isinstance(item, dict),
    }
    if expected in checks and not checks[expected](value):
        raise APIError(422, "TOOL_ARGUMENT_INVALID", f"参数 {name} 类型不正确")
    if expected == "string":
        if "maxLength" in spec and len(value) > int(spec["maxLength"]):
            raise APIError(422, "TOOL_ARGUMENT_INVALID", f"参数 {name} 过长")
        if "enum" in spec and value not in spec["enum"]:
            raise APIError(422, "TOOL_ARGUMENT_INVALID", f"参数 {name} 不在允许范围")
    if expected == "integer":
        if "minimum" in spec and value < int(spec["minimum"]):
            raise APIError(422, "TOOL_ARGUMENT_INVALID", f"参数 {name} 过小")
        if "maximum" in spec and value > int(spec["maximum"]):
            raise APIError(422, "TOOL_ARGUMENT_INVALID", f"参数 {name} 过大")


def validate_arguments(tool: ToolSpec, arguments: dict[str, Any]) -> None:
    if len(str(arguments).encode("utf-8")) > MAX_ARGUMENT_BYTES:
        raise APIError(422, "TOOL_ARGUMENT_INVALID", "工具参数过大")
    properties = tool.schema.get("properties", {})
    required = tool.schema.get("required", [])
    for name in required:
        if name not in arguments:
            raise APIError(422, "TOOL_ARGUMENT_INVALID", f"缺少参数 {name}")
    if tool.schema.get("additionalProperties") is False:
        for name in arguments:
            if name not in properties:
                raise APIError(422, "TOOL_ARGUMENT_INVALID", f"未知参数 {name}")
    for name, value in arguments.items():
        _validate_value(name, value, properties.get(name, {}))


def _current_time(_: Session, arguments: dict[str, Any], __: str) -> dict[str, Any]:
    return {
        "iso": datetime.now(timezone.utc).isoformat(),
        "timezone": str(arguments.get("timezone", "UTC")),
    }


def _catalog_search(session: Session, arguments: dict[str, Any], user_id: str) -> dict[str, Any]:
    query = str(arguments.get("query", "")).strip()
    limit = min(int(arguments.get("limit", 5)), 10)
    visible = CapabilityService(session).public_list(query=query, user_id=user_id)
    items = [
        {
            "id": item.id,
            "name": item.name,
            "kind": item.kind,
            "description": item.description[:200],
        }
        for item in visible
        if item.authorized
        and item.ready
        and item.blockedReason == "none"
        and session.scalar(
            select(CapabilityDefinition.source).where(
                CapabilityDefinition.id == item.id
            )
        )
        != "demo"
    ]
    items = items[:limit]
    return {"items": items, "count": len(items)}


TOOLS: dict[str, ToolSpec] = {
    "system.current_time": ToolSpec(
        name="system.current_time",
        description="Return the current server time. Read-only.",
        side_effect=False,
        schema={
            "type": "object",
            "properties": {"timezone": {"type": "string", "maxLength": 64}},
            "required": [],
            "additionalProperties": False,
        },
        handler=_current_time,
    ),
    "system.catalog_search": ToolSpec(
        name="system.catalog_search",
        description="Search published platform capabilities. Read-only.",
        side_effect=False,
        schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "maxLength": 120},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        handler=_catalog_search,
    ),
}


def get_tool(name: str) -> ToolSpec | None:
    return TOOLS.get(name.strip())


def execute_tool(
    name: str, arguments: dict[str, Any], *, session: Session, user_id: str
) -> dict[str, Any]:
    tool = get_tool(name)
    if tool is None:
        raise APIError(404, "TOOL_NOT_FOUND", "工具不存在")
    if tool.side_effect:
        raise APIError(403, "TOOL_WRITE_BLOCKED", "写操作工具尚未开放")
    validate_arguments(tool, arguments)
    result = tool.handler(session, arguments, user_id)
    if len(str(result).encode("utf-8")) > MAX_RESULT_BYTES:
        raise APIError(422, "TOOL_RESULT_TOO_LARGE", "工具结果过大")
    return result
