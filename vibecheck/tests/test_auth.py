import pytest

from vibecheck.app import create_app


@pytest.mark.asyncio
async def test_health_no_auth(client) -> None:
    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_state_with_valid_psk_header(client, psk: str) -> None:
    response = await client.get("/api/state", headers={"X-PSK": psk})

    assert response.status_code == 200
    assert response.json() == {"total": 0, "running": 0, "waiting": 0, "idle": 0}


@pytest.mark.asyncio
async def test_state_with_valid_psk_query_param(client, psk: str) -> None:
    response = await client.get(f"/api/state?psk={psk}")

    assert response.status_code == 200
    assert response.json() == {"total": 0, "running": 0, "waiting": 0, "idle": 0}


@pytest.mark.asyncio
async def test_state_with_bad_psk_returns_401(client) -> None:
    response = await client.get("/api/state", headers={"X-PSK": "wrong"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


@pytest.mark.asyncio
async def test_state_with_no_psk_returns_401(client) -> None:
    response = await client.get("/api/state")

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_app_startup_fails_when_psk_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIBECHECK_PSK", raising=False)

    with pytest.raises(RuntimeError, match="VIBECHECK_PSK"):
        create_app()
