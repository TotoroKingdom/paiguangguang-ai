"""Chapter 03: a deterministic Session / Turn / Step teaching model.

Python 3.10+. No model API, network, shell commands, or project file access.
This is NOT a port of Codex and does not implement its concurrency or policies.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TurnContext:
    turn_id: int
    task: str


@dataclass(frozen=True)
class StepContext:
    turn: TurnContext
    sampling_number: int
    model: str  # Snapshot of effective settings for this request.


@dataclass(frozen=True)
class ToolCall:
    name: str


@dataclass(frozen=True)
class FinalAnswer:
    text: str


class FakeModel:
    """The responses are scripted to expose sampling boundaries."""

    def sample(self, step: StepContext, observations: list[str]):
        if step.turn.turn_id == 1:
            if len(observations) == 0:
                return ToolCall("inspect_login")
            if len(observations) == 1:
                return ToolCall("inspect_tests")
            return FinalAnswer("登录模块检查完成（模拟）")
        return FinalAnswer("已结合此前记录给出复查意见（模拟）")


TOOLS = {
    "inspect_login": "发现登录模块存在异常处理代码（预置数据）",
    "inspect_tests": "发现登录测试存在失败断言（预置数据）",
}


@dataclass
class Session:
    thread_id: str
    model: str = "mock-v1"
    history: list[str] = field(default_factory=list)
    turns_completed: int = 0
    active_turn: TurnContext | None = None

    def run_turn(self, task: str) -> list[StepContext]:
        if self.active_turn is not None:
            raise RuntimeError("a turn is already active in this demo")

        turn = TurnContext(turn_id=self.turns_completed + 1, task=task)
        self.active_turn = turn
        self.history.append(f"USER: {task}")
        print(f"Turn {turn.turn_id} started: {task}")
        observations: list[str] = []
        steps: list[StepContext] = []
        model = FakeModel()

        try:
            for number in range(1, 6):
                step = StepContext(turn=turn, sampling_number=number, model=self.model)
                steps.append(step)
                result = model.sample(step, observations)
                if isinstance(result, FinalAnswer):
                    self.history.append(f"ASSISTANT: {result.text}")
                    print(f"  Step {number} [{step.model}] -> final: {result.text}")
                    self.turns_completed += 1
                    print(f"Turn {turn.turn_id} completed")
                    return steps

                print(f"  Step {number} [{step.model}] -> tool: {result.name}")
                observation = TOOLS[result.name]
                observations.append(observation)
                self.history.append(f"TOOL: {observation}")
                print(f"    observation: {observation}")

                if turn.turn_id == 1 and number == 1:
                    # Intentional simulation of a settings change BETWEEN requests.
                    self.model = "mock-v2"
                    print("    future sampling settings changed to mock-v2")

            raise RuntimeError("the scripted turn exceeded the step limit")
        finally:
            self.active_turn = None


def main() -> None:
    session = Session(thread_id="demo-thread-1")
    print("Session opened:", session.thread_id)
    first_steps = session.run_turn("检查登录模块")
    second_steps = session.run_turn("继续复查")

    assert [s.model for s in first_steps] == ["mock-v1", "mock-v2", "mock-v2"]
    assert [s.model for s in second_steps] == ["mock-v2"]
    assert session.turns_completed == 2
    assert sum(x.startswith("USER:") for x in session.history) == 2
    assert sum(x.startswith("TOOL:") for x in session.history) == 2
    assert session.active_turn is None
    print("Summary: 1 session, 2 turns, 4 model sampling steps")
    print("All teaching assertions passed")


if __name__ == "__main__":
    main()
