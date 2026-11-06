"""Learn Codex 11: a tiny durable rollout / resume teaching model.

Python 3.10+, standard library only. Uses a temporary directory; no model,
GitHub API, SQL, or existing repository files. NOT Codex's exact wire schema,
truncation algorithm, concurrent writer, or recovery guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os


@dataclass(frozen=True)
class RolloutItem:
    kind: str
    turn_id: str
    payload: str


class ToyThreadStore:
    """Append-order storage with an explicit durability checkpoint."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.pending: list[RolloutItem] = []

    def append(self, item: RolloutItem) -> None:
        self.pending.append(item)

    def flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as fh:
            for item in self.pending:
                line = {"type": item.kind, "turn_id": item.turn_id,
                        "payload": item.payload}
                fh.write(json.dumps(line, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self.pending.clear()

    def resume(self) -> list[RolloutItem]:
        if not self.path.exists():
            return []
        items: list[RolloutItem] = []
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                record = json.loads(line)
                if set(record) != {"type", "turn_id", "payload"}:
                    raise ValueError("invalid fields")
                if not all(isinstance(value, str) for value in record.values()):
                    raise ValueError("invalid field types")
                items.append(RolloutItem(record["type"], record["turn_id"], record["payload"]))
            except (ValueError, TypeError) as exc:
                raise ValueError(f"cannot safely replay line {number}: {exc}") from exc
        return items


def project_ui(items: list[RolloutItem]) -> list[str]:
    """A toy UI projection (not the real Codex event mapping)."""
    return [f"{item.turn_id}: {item.payload}" for item in items
            if item.kind == "event_msg"]


def model_input(items: list[RolloutItem]) -> list[str]:
    """A toy model-history view: NOT a complete Codex reconstruction."""
    return [item.payload for item in items if item.kind == "response_item"]


def turn_state(items: list[RolloutItem], turn_id: str) -> str:
    markers = [x.payload for x in items if x.kind == "event_msg" and x.turn_id == turn_id]
    if "TurnAborted" in markers:
        return "aborted"
    if "TurnComplete" in markers:
        return "completed"
    if "TurnStarted" in markers:
        return "incomplete"
    return "not-started"


def main() -> None:
    with TemporaryDirectory(prefix="learn-codex-11-") as tmp:
        rollout = Path(tmp) / "rollout.jsonl"
        store = ToyThreadStore(rollout)
        store.append(RolloutItem("session_meta", "thread-1", "source=demo"))
        store.append(RolloutItem("event_msg", "turn-1", "TurnStarted"))
        store.append(RolloutItem("response_item", "turn-1", "用户：检查登录模块"))
        store.append(RolloutItem("response_item", "turn-1", "工具观察：模拟测试通过"))
        store.append(RolloutItem("event_msg", "turn-1", "ExecCommandEnd"))
        store.append(RolloutItem("event_msg", "turn-1", "TurnComplete"))
        store.flush()  # Explicit durability boundary.
        print("Persisted first turn (flush complete)")

        store.append(RolloutItem("event_msg", "turn-2", "TurnStarted"))
        store.append(RolloutItem("response_item", "turn-2", "尚未保存的输入"))
        # Simulated process loss BEFORE these pending items reach durable storage.
        reopened = ToyThreadStore(rollout)
        recovered = reopened.resume()
        assert len(recovered) == 6
        assert turn_state(recovered, "turn-1") == "completed"
        assert turn_state(recovered, "turn-2") == "not-started"
        print("Recovered after simulated pre-flush crash: turn-1 completed; turn-2 absent")

        reopened.append(RolloutItem("event_msg", "turn-2", "TurnStarted"))
        reopened.append(RolloutItem("response_item", "turn-2", "用户：取消操作"))
        reopened.append(RolloutItem("event_msg", "turn-2", "TurnAborted"))
        reopened.flush()
        recovered = ToyThreadStore(rollout).resume()
        assert len(recovered) == 9
        assert turn_state(recovered, "turn-2") == "aborted"
        assert len(project_ui(recovered)) == 5
        assert len(model_input(recovered)) == 3
        assert all("Turn" not in text for text in model_input(recovered))
        print("UI event projection:", project_ui(recovered))
        print("Model input projection:", model_input(recovered))
        print("Turn states:", turn_state(recovered, "turn-1"), turn_state(recovered, "turn-2"))
        print("All teaching assertions passed")


if __name__ == "__main__":
    main()
