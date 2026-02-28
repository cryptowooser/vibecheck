from __future__ import annotations

import re
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

INDEX_HTML = Path(__file__).with_name("index.html")

app = FastAPI(title="camera-capture-prototype")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(INDEX_HTML)


def parse_multipart_image(body: bytes, content_type: str) -> tuple[bytes, str, str]:
    match = re.search(r'boundary="?([^";]+)"?', content_type)
    if not match:
        raise HTTPException(status_code=400, detail="missing multipart boundary")

    boundary = f"--{match.group(1)}".encode("utf-8")
    for raw_part in body.split(boundary):
        part = raw_part.strip(b"\r\n")
        if not part or part == b"--":
            continue

        header_bytes, separator, payload = part.partition(b"\r\n\r\n")
        if not separator:
            continue

        header_text = header_bytes.decode("utf-8", errors="ignore")
        if 'name="image"' not in header_text:
            continue

        filename_match = re.search(r'filename="([^"]*)"', header_text)
        type_match = re.search(r"Content-Type:\s*([^\r\n]+)", header_text, re.IGNORECASE)

        file_bytes = payload.rstrip(b"\r\n")
        filename = filename_match.group(1) if filename_match else "upload.bin"
        file_content_type = type_match.group(1) if type_match else "application/octet-stream"
        return file_bytes, filename, file_content_type

    raise HTTPException(status_code=400, detail="missing image field")


@app.post("/upload")
async def upload(request: Request) -> JSONResponse:
    body = await request.body()
    content_type = request.headers.get("content-type", "")
    payload, filename, file_content_type = parse_multipart_image(body, content_type)
    print(f"camera upload: bytes={len(payload)} content_type={file_content_type} filename={filename}")
    return JSONResponse(
        {
            "description": "A whiteboard with code",
            "bytes": len(payload),
            "content_type": file_content_type,
            "filename": filename,
        }
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
