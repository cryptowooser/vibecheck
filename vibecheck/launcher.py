from __future__ import annotations

import argparse
import sys
from typing import Any

import uvicorn

from vibecheck.app import create_app
from vibecheck.bridge import load_vibe_runtime, session_manager
from vibecheck.tui_bridge import TuiBridge


def _fallback_vibe_parser(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run vibecheck live attach")
    parser.add_argument("initial_prompt", nargs="?", default=None)
    parser.add_argument("--teleport", action="store_true")
    parser.add_argument("--agent", default="default")
    parser.add_argument("--enabled-tools", action="append", default=None)
    return parser.parse_args(argv)


def parse_launcher_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, int]:
    raw_args = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--ws-port", type=int, default=7870)
    known, remaining = parser.parse_known_args(raw_args)

    try:
        from vibe.cli.entrypoint import parse_arguments as parse_vibe_args

        original_argv = sys.argv
        sys.argv = [original_argv[0], *remaining]
        try:
            vibe_args = parse_vibe_args()
        finally:
            sys.argv = original_argv
    except Exception:
        vibe_args = _fallback_vibe_parser(remaining)

    return vibe_args, known.ws_port


def build_uvicorn_config(app: Any, port: int) -> uvicorn.Config:
    return uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=port,
        log_level="warning",
        ws="websockets",
    )


try:
    from vibe.cli.textual_ui.app import VibeApp as _BaseVibeApp
except Exception:  # pragma: no cover - covered via tests using fake app class

    class _BaseVibeApp:  # type: ignore[override]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.event_handler = None
            self._loading_widget = None

        def run(self) -> str | None:
            raise RuntimeError("Vibe Textual UI is unavailable")

        def run_worker(self, _worker: Any, *, exclusive: bool = False) -> None:
            _ = exclusive


class VibeCheckApp(_BaseVibeApp):
    def __init__(
        self,
        *,
        agent_loop: object,
        bridge,
        ws_port: int,
        api_app: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(agent_loop=agent_loop, **kwargs)
        self._bridge = bridge
        self._ws_port = ws_port
        self._api_app = api_app
        self._tui_bridge: TuiBridge | None = None

    async def on_mount(self) -> None:
        if hasattr(super(), "on_mount"):
            await super().on_mount()

        if getattr(self, "event_handler", None) is not None:
            self._tui_bridge = TuiBridge(
                self.event_handler,
                loading_state_getter=lambda: getattr(self, "_loading_widget", None) is not None,
                loading_widget_getter=lambda: getattr(self, "_loading_widget", None),
            )
            self._bridge.add_event_listener(self._tui_bridge.on_bridge_event)

        if hasattr(self, "run_worker"):
            self.run_worker(self._run_server(), exclusive=False)

    async def _run_server(self) -> None:
        config = build_uvicorn_config(self._api_app, self._ws_port)
        server = uvicorn.Server(config)
        await server.serve()

    async def _handle_agent_loop_turn(self, prompt: str) -> None:
        self._bridge.inject_message(prompt)

    async def on_unmount(self) -> None:
        if self._tui_bridge is not None:
            self._bridge.remove_event_listener(self._tui_bridge.on_bridge_event)
            self._tui_bridge = None

        if hasattr(super(), "on_unmount"):
            await super().on_unmount()


def _build_agent_loop(vibe_args: argparse.Namespace):
    runtime = load_vibe_runtime()
    config = runtime.vibe_config_cls.load()

    enabled_tools = getattr(vibe_args, "enabled_tools", None)
    if enabled_tools and hasattr(config, "enabled_tools"):
        config.enabled_tools = enabled_tools

    kwargs: dict[str, Any] = {
        "agent_name": getattr(vibe_args, "agent", "default"),
        "enable_streaming": True,
    }

    try:
        loop = runtime.agent_loop_cls(config, **kwargs)
    except TypeError:
        loop = runtime.agent_loop_cls(config)

    return loop, runtime


def launch(argv: list[str] | None = None) -> None:
    vibe_args, ws_port = parse_launcher_args(argv)
    agent_loop, runtime = _build_agent_loop(vibe_args)

    session_id = str(getattr(agent_loop, "session_id", "live-session"))
    bridge = session_manager.attach(session_id, attach_mode="live")
    bridge.attach_to_loop(agent_loop, runtime)

    api_app = create_app()
    app = VibeCheckApp(
        agent_loop=agent_loop,
        bridge=bridge,
        ws_port=ws_port,
        api_app=api_app,
        initial_prompt=getattr(vibe_args, "initial_prompt", None),
        teleport_on_start=getattr(vibe_args, "teleport", False),
    )
    app.run()
