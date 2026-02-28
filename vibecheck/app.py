from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from vibecheck.auth import PSKAuthMiddleware, load_psk
from vibecheck.routes.api import router as api_router
from vibecheck.ws import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.bridge = None
    yield
    app.state.bridge = None


def resolve_static_dir() -> Path:
    configured = os.environ.get("VIBECHECK_STATIC_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parent / "static"


def static_file(path: Path) -> FileResponse:
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(path)


def create_app() -> FastAPI:
    load_psk()
    app = FastAPI(title="vibecheck", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(PSKAuthMiddleware)

    app.include_router(api_router)
    app.include_router(ws_router)

    static_dir = resolve_static_dir()
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    icons_dir = static_dir / "icons"
    if icons_dir.exists():
        app.mount("/icons", StaticFiles(directory=icons_dir), name="icons")

    @app.get("/", include_in_schema=False)
    async def root():
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse({"name": "vibecheck", "status": "ok"})

    @app.get("/manifest.json", include_in_schema=False)
    async def manifest():
        return static_file(static_dir / "manifest.json")

    @app.get("/sw.js", include_in_schema=False)
    async def service_worker():
        return static_file(static_dir / "sw.js")

    return app
