from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from vibecheck.app import create_app


@pytest.fixture
def psk(monkeypatch: pytest.MonkeyPatch) -> str:
    value = "dev-psk"
    monkeypatch.setenv("VIBECHECK_PSK", value)
    return value


@pytest_asyncio.fixture
async def client(psk: str) -> AsyncIterator[AsyncClient]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
