from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ApproveRequest(BaseModel):
    tool_call_id: str
    approved: bool
    edited_args: dict | None = None


class InputRequest(BaseModel):
    text: str


class MessageRequest(BaseModel):
    text: str


@router.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/state")
async def state() -> dict[str, int]:
    return {"total": 0, "running": 0, "waiting": 0, "idle": 0}


@router.get("/api/sessions")
async def list_sessions() -> list[dict]:
    return []


@router.get("/api/sessions/{session_id}")
async def session_detail(session_id: str) -> dict:
    raise HTTPException(status_code=501, detail="not implemented")


@router.post("/api/sessions/{session_id}/approve")
async def approve(session_id: str, body: ApproveRequest) -> dict:
    raise HTTPException(status_code=501, detail="not implemented")


@router.post("/api/sessions/{session_id}/input")
async def input_response(session_id: str, body: InputRequest) -> dict:
    raise HTTPException(status_code=501, detail="not implemented")


@router.post("/api/sessions/{session_id}/message")
async def message(session_id: str, body: MessageRequest) -> dict:
    raise HTTPException(status_code=501, detail="not implemented")
