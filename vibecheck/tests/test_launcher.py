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
    last_kwargs: dict | None = None

    def __init__(self, *_args, **kwargs) -> None:
        self.session_id = "live-session"
        self.message_observer = kwargs.get("message_observer")
        self.approval_callback = None
        self.user_input_callback = None
        FakeAgentLoop.last_kwargs = kwargs

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


def test_build_agent_loop_passes_message_observer(fake_runtime: VibeRuntime) -> None:
    fake_args = SimpleNamespace(agent="default", enabled_tools=None)

    def observer(_message) -> None:
        return None

    loop = launcher._build_agent_loop(fake_args, fake_runtime, message_observer=observer)

    assert loop.message_observer is observer
    assert FakeAgentLoop.last_kwargs is not None
    assert FakeAgentLoop.last_kwargs["message_observer"] is observer


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


@pytest.mark.asyncio
async def test_on_mount_rebinds_callbacks_and_intercepts_future_rebinds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Loop:
        def __init__(self) -> None:
            self.approval_callback = None
            self.user_input_callback = None

        def set_approval_callback(self, callback) -> None:
            self.approval_callback = callback

        def set_user_input_callback(self, callback) -> None:
            self.user_input_callback = callback

    class Bridge:
        def __init__(self) -> None:
            self.attach_calls: list[dict] = []
            self._local_approval_callback = None
            self._local_input_callback = None

        @property
        def local_approval_callback(self):
            return self._local_approval_callback

        @property
        def local_input_callback(self):
            return self._local_input_callback

        async def _approval_callback(self, *_args):
            return ("yes", None)

        async def _user_input_callback(self, *_args):
            return {"response": "ok"}

        def configure_local_callbacks(self, *, approval_callback, input_callback) -> None:
            self._local_approval_callback = approval_callback
            self._local_input_callback = input_callback

        def attach_to_loop(self, agent_loop, *_args, approval_callback=None, input_callback=None, **_kwargs) -> None:
            self.attach_calls.append(
                {
                    "approval_callback": approval_callback,
                    "input_callback": input_callback,
                }
            )
            self.configure_local_callbacks(
                approval_callback=approval_callback,
                input_callback=input_callback,
            )
            agent_loop.set_approval_callback(self._approval_callback)
            agent_loop.set_user_input_callback(self._user_input_callback)

        def add_raw_event_listener(self, _listener) -> None:
            return None

        def remove_raw_event_listener(self, _listener) -> None:
            return None

    async def fake_super_on_mount(self) -> None:
        self.agent_loop.set_approval_callback(lambda *_args: ("yes", None))
        self.agent_loop.set_user_input_callback(lambda *_args: {"response": "ok"})

    monkeypatch.setattr(launcher._BaseVibeApp, "on_mount", fake_super_on_mount, raising=False)

    loop = Loop()
    bridge = Bridge()
    app = launcher.VibeCheckApp(
        agent_loop=loop,
        bridge=bridge,
        ws_port=9001,
        api_app=object(),
    )
    await app.on_mount()

    assert bridge.attach_calls
    assert loop.approval_callback.__func__ is bridge._approval_callback.__func__
    assert loop.user_input_callback.__func__ is bridge._user_input_callback.__func__

    initial_local_approval = bridge.local_approval_callback
    initial_local_input = bridge.local_input_callback
    loop.set_approval_callback(bridge._approval_callback)
    loop.set_user_input_callback(bridge._user_input_callback)
    assert bridge.local_approval_callback is initial_local_approval
    assert bridge.local_input_callback is initial_local_input

    loop.set_approval_callback(lambda *_args: ("no", None))
    loop.set_user_input_callback(lambda *_args: {"response": "later"})
    assert loop.approval_callback.__func__ is bridge._approval_callback.__func__
    assert loop.user_input_callback.__func__ is bridge._user_input_callback.__func__


def test_vibecheck_vibe_script_registered() -> None:
    pyproject = Path("pyproject.toml").read_bytes()
    parsed = tomllib.loads(pyproject.decode("utf-8"))
    scripts = parsed["project"]["scripts"]

    assert scripts["vibecheck-vibe"] == "vibecheck.launcher:launch"
