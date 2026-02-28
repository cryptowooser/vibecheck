from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tomllib

import pytest

from vibecheck.bridge import SessionManager, VibeRuntime
from vibecheck import launcher


class FakeVibeConfig:
    @classmethod
    def load(cls):
        return cls()


class FakeAgentLoop:
    def __init__(self, *_args, **_kwargs) -> None:
        self.session_id = "live-session"
        self.message_observer = None
        self.approval_callback = None
        self.user_input_callback = None

    def set_approval_callback(self, callback) -> None:
        self.approval_callback = callback

    def set_user_input_callback(self, callback) -> None:
        self.user_input_callback = callback


class FakeVibeCheckApp:
    last_instance: "FakeVibeCheckApp | None" = None

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.run_called = False
        FakeVibeCheckApp.last_instance = self

    def run(self):
        self.run_called = True
        return "live-session"


@pytest.fixture
def fake_runtime() -> VibeRuntime:
    return VibeRuntime(
        agent_loop_cls=FakeAgentLoop,
        vibe_config_cls=FakeVibeConfig,
        approval_yes="yes",
        approval_no="no",
        ask_result_cls=None,
        answer_cls=None,
    )


def test_build_uvicorn_config_uses_warning_log_level() -> None:
    config = launcher.build_uvicorn_config(app=object(), port=7870)

    assert config.host == "0.0.0.0"
    assert config.port == 7870
    assert config.log_level == "warning"


def test_launch_creates_live_bridge_and_runs_app(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_runtime: VibeRuntime,
) -> None:
    manager = SessionManager(logs_root=tmp_path / "logs")
    fake_args = SimpleNamespace(
        initial_prompt="hello",
        teleport=False,
        agent="default",
        enabled_tools=None,
    )

    monkeypatch.setenv("VIBECHECK_PSK", "dev-psk")
    monkeypatch.setattr(launcher, "session_manager", manager)
    monkeypatch.setattr(launcher, "parse_launcher_args", lambda argv=None: (fake_args, 9001))
    monkeypatch.setattr(launcher, "load_vibe_runtime", lambda: fake_runtime)
    monkeypatch.setattr(launcher, "create_app", lambda: object())
    monkeypatch.setattr(launcher, "VibeCheckApp", FakeVibeCheckApp)

    launcher.launch([])

    bridge = manager.get("live-session")
    assert bridge.attach_mode == "live"
    assert bridge.controllable is True
    assert FakeVibeCheckApp.last_instance is not None
    assert FakeVibeCheckApp.last_instance.run_called is True
    assert FakeVibeCheckApp.last_instance.kwargs["ws_port"] == 9001


def test_vibecheck_vibe_script_registered() -> None:
    pyproject = Path("pyproject.toml").read_bytes()
    parsed = tomllib.loads(pyproject.decode("utf-8"))
    scripts = parsed["project"]["scripts"]

    assert scripts["vibecheck-vibe"] == "vibecheck.launcher:launch"
