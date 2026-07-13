from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from app.chatbot.memory.semantic_memory import MemoryIndexRebuilder, SemanticMemoryIndex
from app.chatbot.repositories.memory_repository import MemoryRepository
from app.core.config import Settings, get_settings
from app.db.session import build_session_factory


class MemoryIndexCommand:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        memory_repository: MemoryRepository | None = None,
        semantic_index: SemanticMemoryIndex | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.semantic_index = semantic_index or SemanticMemoryIndex(settings=self.settings)
        if memory_repository is None:
            memory_repository = MemoryRepository(build_session_factory(self.settings))
        self.rebuilder = MemoryIndexRebuilder(
            memory_repository=memory_repository,
            semantic_index=self.semantic_index,
            settings=self.settings,
        )

    def dry_run(self, user_id: str):
        return self.rebuilder.dry_run(user_id)

    def apply(self, user_id: str):
        return self.rebuilder.apply(user_id)

    def count(self, user_id: str) -> int:
        return self.rebuilder.count(user_id)

    def checksum(self, user_id: str) -> str:
        return self.rebuilder.checksum(user_id)

    def switch(self, user_id: str):
        return self.rebuilder.switch(user_id)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rebuild chatbot semantic memory index")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Report active memory count and checksum without writing")
    group.add_argument("--apply", action="store_true", help="Rebuild the semantic index from PostgreSQL")
    group.add_argument("--count", action="store_true", help="Print the active memory count")
    group.add_argument("--checksum", action="store_true", help="Print the active memory checksum")
    group.add_argument("--switch", action="store_true", help="Rebuild and switch to the current semantic index")
    parser.add_argument("--user-id", required=True, help="Owner user id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = MemoryIndexCommand()
    if args.dry_run:
        report = command.dry_run(args.user_id)
        print(json.dumps(asdict(report), ensure_ascii=False))
        return 0
    if args.apply:
        report = command.apply(args.user_id)
        print(json.dumps(asdict(report), ensure_ascii=False))
        return 0
    if args.count:
        print(command.count(args.user_id))
        return 0
    if args.checksum:
        print(command.checksum(args.user_id))
        return 0
    if args.switch:
        report = command.switch(args.user_id)
        print(json.dumps(asdict(report), ensure_ascii=False))
        return 0
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
