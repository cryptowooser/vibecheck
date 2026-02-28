from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

INDEX_HTML = Path(__file__).with_name("index.html")

app = FastAPI(title="camera-capture-prototype")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(INDEX_HTML)


@app.post("/upload")
async def upload(request: Request) -> JSONResponse:
    payload = await request.body()
    content_type = request.headers.get("content-type", "application/octet-stream")
    print(f"camera upload: bytes={len(payload)} content_type={content_type}")
    return JSONResponse(
        {
            "description": "A whiteboard with code",
            "bytes": len(payload),
            "content_type": content_type,
        }
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
