from __future__ import annotations

from types import SimpleNamespace

from vibecheck import launcher
from vibecheck.bridge import VibeRuntime


class FakeVibeConfig:
    load_calls = 0

    @classmethod
    def load(cls):
        cls.load_calls += 1
        return cls()


class FakeAgentLoop:
    def __init__(self, *_args, **kwargs) -> None:
        self.session_id = "unlock-test"
        self.kwargs = kwargs


def test_build_agent_loop_unlocks_vibe_config_paths(monkeypatch) -> None:
    unlock_calls: list[str] = []

    def fake_unlock() -> None:
        unlock_calls.append("called")

    monkeypatch.setattr(launcher, "_unlock_vibe_config_paths", fake_unlock)

    runtime = VibeRuntime(
        agent_loop_cls=FakeAgentLoop,
        vibe_config_cls=FakeVibeConfig,
        approval_yes="yes",
        approval_no="no",
        ask_result_cls=None,
        answer_cls=None,
    )
    args = SimpleNamespace(agent="default", enabled_tools=None)

    loop = launcher._build_agent_loop(args, runtime)

    assert unlock_calls == ["called"]
    assert FakeVibeConfig.load_calls == 1
    assert isinstance(loop, FakeAgentLoop)
