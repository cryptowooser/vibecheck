from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from vibecheck.app import create_app


@pytest_asyncio.fixture
async def static_client(monkeypatch: pytest.MonkeyPatch, tmp_path) -> AsyncIterator[AsyncClient]:
    static_dir = tmp_path / "static"
    (static_dir / "assets").mkdir(parents=True)
    (static_dir / "icons").mkdir(parents=True)

    (static_dir / "index.html").write_text(
        """
<!doctype html>
<html lang="en">
  <head>
    <link rel="manifest" href="/manifest.json" />
    <link rel="icon" type="image/png" href="/icons/vibe-192.png" />
    <script type="module" src="/assets/index-test.js"></script>
  </head>
  <body>
    <div id="app"></div>
  </body>
</html>
""".strip(),
        encoding="utf-8",
    )
    (static_dir / "assets" / "index-test.js").write_text("console.log('ok')\n", encoding="utf-8")
    (static_dir / "manifest.json").write_text('{"name":"vibecheck"}\n', encoding="utf-8")
    (static_dir / "sw.js").write_text("self.addEventListener('push', ()=>{})\n", encoding="utf-8")
    (static_dir / "icons" / "vibe-192.png").write_bytes(b"png-placeholder")

    monkeypatch.setenv("VIBECHECK_PSK", "dev-psk")
    monkeypatch.setenv("VIBECHECK_STATIC_DIR", str(static_dir))

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_backend_serves_frontend_root_assets_and_pwa_files(static_client: AsyncClient) -> None:
    for path in ("/", "/assets/index-test.js", "/manifest.json", "/sw.js", "/icons/vibe-192.png"):
        response = await static_client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"
