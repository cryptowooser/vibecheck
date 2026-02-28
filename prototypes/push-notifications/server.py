from __future__ import annotations

import asyncio
import json
from base64 import urlsafe_b64encode
from pathlib import Path

import uvicorn
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from py_vapid import Vapid01
from pywebpush import WebPushException, webpush

BASE_DIR = Path(__file__).resolve().parent
INDEX_HTML = BASE_DIR / "index.html"
SW_JS = BASE_DIR / "sw.js"
VAPID_KEYS_FILE = BASE_DIR / "vapid_keys.json"
SUBSCRIPTIONS_FILE = BASE_DIR / "subscriptions.json"

app = FastAPI(title="push-notifications-prototype")
icons_dir = BASE_DIR / "icons"
if icons_dir.exists():
    app.mount("/icons", StaticFiles(directory=icons_dir), name="icons")


class PushStore:
    def __init__(self) -> None:
        self.vapid_public_key_b64 = ""
        self.vapid_private_key_pem = ""
        self.vapid_subject = "mailto:vibecheck@example.com"
        self.subscriptions: list[dict] = []
        self._load_or_create_vapid_keys()
        self._load_subscriptions()

    def _load_or_create_vapid_keys(self) -> None:
        if VAPID_KEYS_FILE.exists():
            payload = json.loads(VAPID_KEYS_FILE.read_text(encoding="utf-8"))
            self.vapid_private_key_pem = payload["private_key_pem"]
            self.vapid_public_key_b64 = payload["public_key_b64"]
            return

        vapid = Vapid01()
        vapid.generate_keys()
        public_bytes = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)

        self.vapid_private_key_pem = vapid.private_pem().decode("utf-8")
        self.vapid_public_key_b64 = urlsafe_b64encode(public_bytes).decode("utf-8").rstrip("=")

        VAPID_KEYS_FILE.write_text(
            json.dumps(
                {
                    "public_key_b64": self.vapid_public_key_b64,
                    "private_key_pem": self.vapid_private_key_pem,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _load_subscriptions(self) -> None:
        if not SUBSCRIPTIONS_FILE.exists():
            self.subscriptions = []
            return
        self.subscriptions = json.loads(SUBSCRIPTIONS_FILE.read_text(encoding="utf-8"))

    def save_subscriptions(self) -> None:
        SUBSCRIPTIONS_FILE.write_text(json.dumps(self.subscriptions, indent=2), encoding="utf-8")

    def add_subscription(self, payload: dict) -> bool:
        endpoint = payload.get("endpoint")
        if not endpoint:
            return False
        if any(existing.get("endpoint") == endpoint for existing in self.subscriptions):
            return True
        self.subscriptions.append(payload)
        self.save_subscriptions()
        return True


store = PushStore()


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(INDEX_HTML)


@app.get("/sw.js")
async def service_worker() -> FileResponse:
    return FileResponse(SW_JS, media_type="application/javascript")


@app.get("/vapid-public-key")
async def vapid_public_key() -> JSONResponse:
    return JSONResponse({"publicKey": store.vapid_public_key_b64})


@app.post("/subscribe")
async def subscribe(request: Request) -> JSONResponse:
    payload = await request.json()
    if not store.add_subscription(payload):
        return JSONResponse({"status": "error", "detail": "missing endpoint"}, status_code=400)
    return JSONResponse({"status": "ok", "count": len(store.subscriptions)})


@app.post("/send-test")
async def send_test(request: Request) -> JSONResponse:
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    notification = {
        "title": body.get("title", "Vibe Check"),
        "body": body.get("body", "Approval needed."),
        "type": "approval",
    }

    sent = 0
    failed = 0
    errors: list[str] = []

    for subscription in store.subscriptions:
        try:
            await asyncio.to_thread(
                webpush,
                subscription_info=subscription,
                data=json.dumps(notification),
                vapid_private_key=store.vapid_private_key_pem,
                vapid_claims={"sub": store.vapid_subject},
                ttl=30,
                timeout=5,
            )
            sent += 1
        except WebPushException as exc:
            failed += 1
            errors.append(str(exc))
        except Exception as exc:  # pragma: no cover - defensive catch for prototype
            failed += 1
            errors.append(str(exc))

    return JSONResponse(
        {
            "status": "ok",
            "attempted": len(store.subscriptions),
            "sent": sent,
            "failed": failed,
            "errors": errors[:3],
        }
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
