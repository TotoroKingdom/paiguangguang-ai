"""A1: safe teaching model of project instructions and explicit Skill injection.

Python 3.10+, standard library only. A fake in-memory filesystem; never scans
real directories, executes tools, imports YAML parsers or calls a model.
NOT a drop-in implementation of the Codex Rust loaders or security checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    path: str
    body: str
    enabled: bool = True


def ancestor_dirs(cwd: str, files: dict[str, str], markers: tuple[str, ...] = (".git",)) -> list[str]:
    """Toy project-root detection: nearest ancestor with a named marker."""
    path = PurePosixPath(cwd)
    parents = [path, *path.parents]
    root = next((p for p in parents if any(str(p / m) in files for m in markers)), None)
    if root is None:
        return [str(path)]  # Mirrors no-root current-directory behavior.
    result = []
    while path != root:
        result.append(str(path))
        path = path.parent
    result.append(str(root))
    return list(reversed(result))


def discover_project_docs(
    cwd: str, files: dict[str, str], *, trusted: bool = True,
    max_bytes: int = 2048, fallbacks: tuple[str, ...] = (),
) -> list[tuple[str, str]]:
    if not trusted:
        return []
    # Same conceptual precedence per directory; no real URI / remote FS checks.
    valid = tuple(name for name in fallbacks
                  if name not in ("", ".", "..") and "/" not in name and "\\" not in name)
    filenames = ("AGENTS.override.md", "AGENTS.md", *valid)
    out: list[tuple[str, str]] = []
    remaining = max_bytes
    for folder in ancestor_dirs(cwd, files):
        for name in filenames:
            path = str(PurePosixPath(folder) / name)
            if path not in files:
                continue
            if remaining <= 0:
                return out
            # This teaching fixture is ASCII, so byte truncation is deterministic.
            content = files[path].encode("utf-8")[:remaining].decode("utf-8", errors="replace")
            if content.strip():
                out.append((path, content))
                remaining -= len(content.encode("utf-8"))
            break  # Exactly one preferred file from each folder.
    return out


def combine_instructions(host_user: str, thread: str, docs: list[tuple[str, str]]) -> str:
    prefix = [value for value in (host_user, thread) if value.strip()]
    body = "\n\n".join(value for _, value in docs)
    if prefix and body:
        return "\n\n".join(prefix) + "\n\n--- project-doc ---\n\n" + body
    return "\n\n".join([*prefix, body] if body else prefix)


def select_explicit_skills(message: str, skills: list[Skill], structured_paths: tuple[str, ...] = ()) -> list[Skill]:
    """Simplified: explicit paths first, then unambiguous $name mentions."""
    picked: list[Skill] = []
    seen: set[str] = set()
    for path in structured_paths:
        for skill in skills:
            if skill.path == path and skill.enabled and path not in seen:
                picked.append(skill)
                seen.add(path)
    names = re.findall(r"(?<!\w)\$([A-Za-z][A-Za-z0-9_-]*)", message)
    for name in names:
        matches = [s for s in skills if s.enabled and s.name == name]
        if len(matches) == 1 and matches[0].path not in seen:
            picked.append(matches[0])
            seen.add(matches[0].path)
    return picked


def inject_skills(selected: list[Skill]) -> list[dict[str, str]]:
    # In real Codex, HostSkillPrompts produces ContextualUserFragment items.
    return [{"role": "user", "kind": "skill_instructions", "source": s.path,
             "body": s.body} for s in selected]


def main() -> None:
    files = {
        "/repo/.git": "directory-marker",
        "/repo/AGENTS.md": "Root: tests only, no mass formatting.",
        "/repo/api/AGENTS.md": "API: run focused unit tests.",
        "/repo/api/AGENTS.override.md": "API override: inspect before editing.",
        "/repo/api/auth/AGENTS.md": "Auth: do not print tokens.",
        "/repo/other/AGENTS.md": "Unrelated: should not load.",
        "/repo/api/auth/POLICY.txt": "not discovered by default",
    }
    docs = discover_project_docs("/repo/api/auth", files)
    assert [path for path, _ in docs] == [
        "/repo/AGENTS.md", "/repo/api/AGENTS.override.md", "/repo/api/auth/AGENTS.md"
    ]
    assert all("Unrelated" not in body for _, body in docs)
    assert not discover_project_docs("/repo/api/auth", files, trusted=False)
    assert [p for p, _ in discover_project_docs("/repo/api/auth", files, max_bytes=10)] == ["/repo/AGENTS.md"]
    assert ancestor_dirs("/tmp/no-repo", files) == ["/tmp/no-repo"]
    merged = combine_instructions("Host instructions", "Thread instructions", docs)
    assert merged.index("Host instructions") < merged.index("Thread instructions") < merged.index("Root:")
    print("AGENTS.md discovery order:", [path for path, _ in docs])
    print("Instruction role: user (not system); project-doc separator present:", "--- project-doc ---" in merged)

    skills = [
        Skill("review", "Review code safely", "/repo/.agents/skills/review/SKILL.md", "Steps: inspect, report."),
        Skill("tests", "Run focused tests", "/repo/.agents/skills/tests/SKILL.md", "Steps: select unit tests."),
        Skill("deploy", "Production deployment", "/repo/.agents/skills/deploy/SKILL.md", "Never run in this demo.", False),
        Skill("review", "Another review skill", "/external/review/SKILL.md", "Ambiguous name."),
    ]
    assert not select_explicit_skills("Please review code", skills)
    assert not select_explicit_skills("Use $review", skills)  # Ambiguous plain name.
    assert not select_explicit_skills("Use $deploy", skills)  # Disabled.
    selected = select_explicit_skills("Use $tests then inspect", skills,
                                     structured_paths=("/repo/.agents/skills/review/SKILL.md",))
    assert [s.name for s in selected] == ["review", "tests"]
    fragments = inject_skills(selected)
    assert all(fragment["role"] == "user" for fragment in fragments)
    assert len(fragments) == 2 and len(skills) == 4
    print("Discovered Skill metadata:", [s.name for s in skills])
    print("Injected Skill bodies:", [f["source"] for f in fragments])
    print("Unmentioned, ambiguous, or disabled Skill bodies were not injected")
    print("All teaching assertions passed")


if __name__ == "__main__":
    main()
