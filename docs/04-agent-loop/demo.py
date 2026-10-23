"""Chapter 04: a safe, deterministic Agent Loop learning example.

Python 3.10+. No API key, network access, shell commands, or file writes.
All model decisions and tool observations are predefined teaching data.
This code is NOT an implementation of the Codex API or security model.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str


@dataclass(frozen=True)
class FinalAnswer:
    text: str


Response = ToolCall | FinalAnswer


@dataclass
class Turn:
    prompt: str
    history: list[dict[str, str]] = field(default_factory=list)
    samples: int = 0
    finished: bool = False


class FakeModel:
    """One model sampling per call; a scripted decision based on tool evidence."""

    def sample(self, turn: Turn) -> Response:
        outputs = [m for m in turn.history if m["role"] == "tool"]
        if turn.prompt == "你好":
            return FinalAnswer("你好！无需工具。")
        if not outputs:
            return ToolCall("call-1", "inspect_login")
        if len(outputs) == 1:
            return ToolCall("call-2", "inspect_tests")
        return FinalAnswer("分析完成：检查了登录代码与相关测试（模拟结果）。")


class MockTools:
    """A deliberately small allowlist: never executes arbitrary commands."""

    _results = {
        "inspect_login": "登录代码中有待检查的异常分支（预置观察）",
        "inspect_tests": "相关测试存在失败断言（预置观察）",
    }

    def execute(self, call: ToolCall) -> str:
        if call.name not in self._results:
            return f"工具错误：不支持 {call.name}"
        return self._results[call.name]


class MiniAgentRuntime:
    def __init__(self, max_samplings: int = 5) -> None:
        self.model = FakeModel()
        self.tools = MockTools()
        self.max_samplings = max_samplings

    def run_turn(self, prompt: str) -> Turn:
        turn = Turn(prompt=prompt, history=[{"role": "user", "content": prompt}])
        print(f"Turn started: {prompt}")

        for step in range(1, self.max_samplings + 1):
            turn.samples = step
            print(f"  sampling {step}: request model")
            response = self.model.sample(turn)

            if isinstance(response, FinalAnswer):
                turn.history.append({"role": "assistant", "content": response.text})
                turn.finished = True
                print(f"  final answer: {response.text}")
                print("Turn completed")
                return turn

            print(f"  tool request: {response.name} [{response.call_id}]")
            observation = self.tools.execute(response)
            turn.history.append({"role": "tool", "content": observation})
            print(f"  tool observation: {observation}")
            # The next iteration builds a new model request with the observation.

        raise RuntimeError("Teaching guard: maximum model samplings reached")


def main() -> None:
    agent = MiniAgentRuntime(max_samplings=5)
    analyzed = agent.run_turn("分析登录问题")
    assert analyzed.finished and analyzed.samples == 3
    assert [m["role"] for m in analyzed.history] == ["user", "tool", "tool", "assistant"]

    greeted = agent.run_turn("你好")
    assert greeted.finished and greeted.samples == 1
    assert [m["role"] for m in greeted.history] == ["user", "assistant"]

    try:
        MiniAgentRuntime(max_samplings=1).run_turn("分析登录问题")
    except RuntimeError as error:
        print(f"Guard triggered: {error}")
    else:
        raise AssertionError("the sampling limit should have stopped the demo")

    print("All teaching assertions passed")


if __name__ == "__main__":
    main()
