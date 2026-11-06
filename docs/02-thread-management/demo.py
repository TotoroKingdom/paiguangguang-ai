"""Learn Codex · Chapter 02: a tiny in-memory Thread manager.

Run: python demo.py
No network, API key, file modifications, or external dependencies.
Educational simulation — NOT actual Codex APIs or concurrency behavior.
"""

from collections import deque
from dataclasses import dataclass, field


@dataclass
class Session:
    """A tiny stand-in for session-owned state."""

    messages: list[str] = field(default_factory=list)


@dataclass
class MiniThread:
    thread_id: str
    session: Session = field(default_factory=Session)
    events: deque[str] = field(default_factory=deque)
    closed: bool = False

    def submit(self, text: str) -> None:
        if self.closed:
            raise RuntimeError(f"{self.thread_id} is closed")
        self.session.messages.append(text)
        self.events.append(f"task/accepted: {text}")
        # The model/tool loop is intentionally outside this chapter.
        self.events.append(f"turn/completed: processed {len(self.session.messages)} message(s)")

    def next_event(self) -> str | None:
        return self.events.popleft() if self.events else None

    def shutdown(self) -> None:
        self.closed = True


class MiniThreadManager:
    def __init__(self) -> None:
        self._threads: dict[str, MiniThread] = {}
        self._counter = 0

    def start_thread(self) -> MiniThread:
        self._counter += 1
        thread = MiniThread(thread_id=f"demo-{self._counter}")
        self._threads[thread.thread_id] = thread
        return thread

    def get_thread(self, thread_id: str) -> MiniThread:
        return self._threads[thread_id]

    def remove_thread(self, thread_id: str) -> MiniThread:
        # Detach from the registry, not equivalent to shutdown/delete history.
        return self._threads.pop(thread_id)

    def list_thread_ids(self) -> list[str]:
        return sorted(self._threads)


def drain(thread: MiniThread) -> None:
    while (event := thread.next_event()) is not None:
        print(f"[{thread.thread_id}] {event}")


def main() -> None:
    manager = MiniThreadManager()
    login = manager.start_thread()
    tests = manager.start_thread()
    print("created:", manager.list_thread_ids())

    login.submit("检查登录模块")
    tests.submit("分析测试失败")
    login.submit("继续定位异常处理")

    assert manager.get_thread(login.thread_id) is login
    assert login.session.messages == ["检查登录模块", "继续定位异常处理"]
    assert tests.session.messages == ["分析测试失败"]
    drain(login)
    drain(tests)

    detached = manager.remove_thread(login.thread_id)
    print("after remove:", manager.list_thread_ids())
    assert detached is login
    assert not detached.closed
    try:
        manager.get_thread(login.thread_id)
    except KeyError:
        print("lookup removed thread: not found")
    else:
        raise AssertionError("removed thread should not be registered")

    # Lifecycle change is an explicit *separate* operation.
    detached.shutdown()
    print("detached thread closed:", detached.closed)
    assert manager.get_thread(tests.thread_id) is tests
    print("other thread remains:", tests.thread_id)


if __name__ == "__main__":
    main()
