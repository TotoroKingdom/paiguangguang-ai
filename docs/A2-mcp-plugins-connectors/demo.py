"""A2: a safe, offline MCP catalog/handler/approval snapshot teaching model.

Python 3.10+; standard library only. No actual MCP connection, OAuth, server,
filesystem, network or external plugin. Model names are simplified placeholders.
"""
from __future__ import annotations

from dataclasses import dataclass
import asyncio
import json


@dataclass(frozen=True)
class ToolInfo:
    server: str
    raw_name: str
    callable_namespace: str
    callable_name: str
    required_field: str = "query"
    model_visible: bool = True
    enabled: bool = True
    deferred: bool = False
    needs_approval: bool = False
    connector_id: str | None = None

    @property
    def model_name(self) -> str:
        # Simplified encoding; real Codex normalizes and resolves collisions.
        return f"{self.callable_namespace}.{self.callable_name}"


@dataclass(frozen=True)
class CallToolResult:
    text: str
    is_error: bool = False


@dataclass(frozen=True)
class HandlerResult:
    status: str
    call_id: str
    raw_target: str = ""
    text: str = ""


class FakeMcpClient:
    def __init__(self, server: str, revision: str) -> None:
        self.server, self.revision = server, revision
        self.calls = 0

    async def call_tool(self, raw_name: str, arguments: dict) -> CallToolResult:
        self.calls += 1
        if arguments.get("query") == "fail":
            return CallToolResult("simulated remote tool failure", is_error=True)
        return CallToolResult(f"{self.server}@{self.revision}/{raw_name}: {arguments}")


class Binding:
    """Immutable *catalog and client selection*, approximating McpBinding."""

    def __init__(self, infos: list[ToolInfo], clients: dict[str, FakeMcpClient],
                 enabled_connectors: frozenset[str] = frozenset()) -> None:
        self._clients = dict(clients)
        self._registered: dict[str, ToolInfo] = {}
        self._direct: set[str] = set()
        for info in infos:
            if not info.enabled or not info.model_visible:
                continue
            if info.connector_id and info.connector_id not in enabled_connectors:
                continue
            if info.server not in clients:
                continue
            if info.model_name in self._registered:
                raise ValueError(f"colliding callable name: {info.model_name}")
            self._registered[info.model_name] = info
            if not info.deferred:
                self._direct.add(info.model_name)

    def model_tool_specs(self) -> list[str]:
        return sorted(self._direct)

    def discover_deferred(self) -> list[str]:
        return sorted(set(self._registered) - self._direct)

    async def invoke(self, model_name: str, raw_arguments: str, *,
                     call_id: str, approved: bool = False,
                     deferred_discovered: bool = False) -> HandlerResult:
        info = self._registered.get(model_name)
        if info is None:
            return HandlerResult("not-available", call_id)
        if model_name not in self._direct and not deferred_discovered:
            return HandlerResult("not-exposed-yet", call_id)
        try:
            args = json.loads(raw_arguments)
        except json.JSONDecodeError:
            return HandlerResult("invalid-json", call_id)
        if not isinstance(args, dict) or not isinstance(args.get(info.required_field), str):
            return HandlerResult("invalid-arguments", call_id)
        if info.needs_approval and not approved:
            return HandlerResult("approval-denied", call_id)
        client = self._clients[info.server]
        result = await client.call_tool(info.raw_name, args)
        return HandlerResult(
            "tool-error" if result.is_error else "completed",
            call_id, f"{info.server}/{info.raw_name}", result.text
        )


async def run_demo() -> None:
    specs = [
        ToolInfo("github", "read_file", "mcp__github", "read_file"),
        ToolInfo("github", "search_code", "mcp__github", "search_code", deferred=True),
        ToolInfo("github", "private_admin", "mcp__github", "private_admin", model_visible=False),
        ToolInfo("github", "delete_repo", "mcp__github", "delete_repo", enabled=False),
        ToolInfo("apps", "search_crm", "mcp__apps", "search_crm", connector_id="crm"),
        ToolInfo("apps", "update_crm", "mcp__apps", "update_crm",
                 connector_id="crm", needs_approval=True),
    ]
    github_v1 = FakeMcpClient("github", "v1")
    apps_v1 = FakeMcpClient("apps", "v1")
    old = Binding(specs, {"github": github_v1, "apps": apps_v1},
                  enabled_connectors=frozenset({"crm"}))
    print("Direct model ToolSpecs:", old.model_tool_specs())
    print("Deferred registry entries:", old.discover_deferred())
    assert len(old.model_tool_specs()) == 3
    assert old.discover_deferred() == ["mcp__github.search_code"]

    async def check(binding: Binding, name: str, arguments: str, want: str,
                    cid: str, **kwargs) -> HandlerResult:
        result = await binding.invoke(name, arguments, call_id=cid, **kwargs)
        assert result.status == want, (cid, result.status, want)
        assert result.call_id == cid
        print(f"{cid}: {name} -> {result.status}")
        return result

    good = await check(old, "mcp__github.read_file", '{"query":"README.md"}',
                       "completed", "call-1")
    assert good.raw_target == "github/read_file" and "github@v1" in good.text
    await check(old, "mcp__github.read_file", "{invalid", "invalid-json", "call-2")
    await check(old, "mcp__github.read_file", '{"nope": 1}', "invalid-arguments", "call-3")
    await check(old, "mcp__github.private_admin", '{"query":"x"}', "not-available", "call-4")
    await check(old, "mcp__github.delete_repo", '{"query":"x"}', "not-available", "call-5")
    await check(old, "mcp__github.search_code", '{"query":"bug"}', "not-exposed-yet", "call-6")
    await check(old, "mcp__github.search_code", '{"query":"bug"}', "completed",
                "call-7", deferred_discovered=True)
    await check(old, "mcp__apps.update_crm", '{"query":"change"}', "approval-denied", "call-8")
    await check(old, "mcp__apps.update_crm", '{"query":"change"}', "completed",
                "call-9", approved=True)
    await check(old, "mcp__github.read_file", '{"query":"fail"}', "tool-error", "call-10")

    restricted = Binding(specs, {"github": github_v1, "apps": apps_v1})
    await check(restricted, "mcp__apps.search_crm", '{"query":"x"}', "not-available", "call-11")

    # Catalog publication changes current tools/clients; old binding is still pinned.
    github_v2 = FakeMcpClient("github", "v2")
    current = Binding(specs, {"github": github_v2, "apps": apps_v1},
                      enabled_connectors=frozenset({"crm"}))
    prior = await check(old, "mcp__github.read_file", '{"query":"README.md"}',
                        "completed", "call-12")
    fresh = await check(current, "mcp__github.read_file", '{"query":"README.md"}',
                        "completed", "call-13")
    assert "github@v1" in prior.text and "github@v2" in fresh.text
    print("Published v2 catalog without retargeting the v1 binding")
    assert github_v1.calls == 4 and github_v2.calls == 1
    print("All teaching assertions passed")


if __name__ == "__main__":
    asyncio.run(run_demo())
