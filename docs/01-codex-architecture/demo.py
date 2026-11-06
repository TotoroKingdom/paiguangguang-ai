"""第一章教学模拟：客户端 -> 服务接口 -> Agent Runtime -> 工具。

仅用 Python 标准库；不访问网络、不读取项目文件、不修改磁盘。
这不是 Codex 源码的 Python 移植，也不模拟它的权限与隔离机制。
"""

from dataclasses import dataclass


@dataclass
class ToolCall:
    name: str


@dataclass
class FinalAnswer:
    text: str


class FakeModel:
    """用确定性规则代替真实大模型，便于观察消息流。"""

    def reply(self, history: list[dict]) -> ToolCall | FinalAnswer:
        if not any(item["role"] == "tool" for item in history):
            return ToolCall("read_project_info")
        return FinalAnswer("已收到模拟项目资料。下一步应检查登录异常处理逻辑。")


class SafeTools:
    """工具结果是预置的教学数据，并未读取真实仓库。"""

    def execute(self, call: ToolCall) -> str:
        if call.name != "read_project_info":
            raise ValueError("Unknown teaching tool")
        return "【模拟资料】项目包含登录模块；异常处理逻辑需要进一步检查。"


class AgentRuntime:
    def __init__(self) -> None:
        self.model = FakeModel()
        self.tools = SafeTools()
        self.next_thread_id = 1

    def run(self, user_task: str):
        thread_id = f"demo-{self.next_thread_id}"
        self.next_thread_id += 1
        history = [{"role": "user", "content": user_task}]
        yield "thread/started", thread_id

        for _ in range(5):
            answer = self.model.reply(history)
            if isinstance(answer, FinalAnswer):
                yield "turn/completed", answer.text
                return

            yield "tool/call", answer.name
            observation = self.tools.execute(answer)
            yield "tool/result", observation
            history.append({"role": "tool", "content": observation})

        raise RuntimeError("Teaching loop exceeded the safety limit")


class AppServer:
    """演示服务接口负责转交请求与事件；并不启动服务器。"""

    def __init__(self) -> None:
        self.runtime = AgentRuntime()

    def submit(self, task: str):
        yield from self.runtime.run(task)


def main() -> None:
    app_server = AppServer()
    task = "请分析项目的登录问题，先不要修改文件"
    print(f"Client > {task}")
    for event_name, payload in app_server.submit(task):
        print(f"{event_name} > {payload}")


if __name__ == "__main__":
    main()
