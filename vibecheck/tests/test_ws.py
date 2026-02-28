from __future__ import annotations

from concurrent.futures import CancelledError

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from vibecheck.app import create_app
from vibecheck import ws as ws_module


@pytest.fixture
def ws_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("VIBECHECK_PSK", "dev-psk")
    ws_module.manager.active_connections.clear()
    app = create_app()
    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()
        ws_module.manager.active_connections.clear()


def test_ws_rejects_invalid_psk(ws_client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as exc:
        with ws_client.websocket_connect("/ws/events/session-1?psk=bad"):
            pass

    assert exc.value.code == 4401


def test_ws_connects_with_valid_psk_and_sends_connected_event(ws_client: TestClient) -> None:
    payload: dict | None = None
    try:
        with ws_client.websocket_connect("/ws/events/session-2?psk=dev-psk") as websocket:
            payload = websocket.receive_json()
            websocket.close()
    except CancelledError:
        # TestClient may bubble a close-time cancellation from the background portal.
        pass

    assert payload == {"type": "connected", "session_id": "session-2"}


def test_ws_heartbeat_failure_still_cleans_up_connection(
    monkeypatch: pytest.MonkeyPatch, ws_client: TestClient
) -> None:
    async def failing_heartbeat(_websocket) -> None:
        raise RuntimeError("heartbeat failure")

    monkeypatch.setattr(ws_module, "_send_heartbeats", failing_heartbeat)

    with ws_client.websocket_connect("/ws/events/session-3?psk=dev-psk") as websocket:
        payload = websocket.receive_json()
        assert payload == {"type": "connected", "session_id": "session-3"}

    assert ws_module.manager.active_connections == {}
