from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

INDEX_HTML = Path(__file__).with_name("index.html")

app = FastAPI(title="media-recorder-prototype")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(INDEX_HTML)


@app.post("/upload")
async def upload(request: Request) -> JSONResponse:
    payload = await request.body()
    content_type = request.headers.get("content-type", "application/octet-stream")
    print(f"upload received: bytes={len(payload)} content_type={content_type}")
    duration_ms = max(1, min(300000, len(payload)))
    return JSONResponse(
        {
            "text": "テスト",
            "language": "ja",
            "duration_ms": duration_ms,
            "bytes": len(payload),
            "content_type": content_type,
        }
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
