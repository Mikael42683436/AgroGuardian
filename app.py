import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

DEVICE_KEY = "278088d6-b723-45eb-8005-e7dc4b9e00ab"
BOUNDARY = "agroguardianframe"
LIVE_SECONDS = 45

latest_frame: bytes | None = None
last_frame_at: float | None = None
live_until = 0.0
frame_event = asyncio.Event()


def require_device_key(value: str) -> None:
    if value != DEVICE_KEY:
        raise HTTPException(status_code=401, detail="Chave de dispositivo inválida.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="AgroGuardian ESP32 Test Live", lifespan=lifespan)


@app.get("/")
def root():
    return {"ok": True, "service": "agroguardian-esp32-test-live"}


@app.get("/health")
def health():
    return {"ok": True, "device_key_configured": True}


@app.post("/api/live/request/{device_key}")
def request_live(device_key: str):
    global live_until
    require_device_key(device_key)
    live_until = time.monotonic() + LIVE_SECONDS
    return {"ok": True, "live": True, "expires_in_seconds": LIVE_SECONDS}


@app.get("/api/live/status")
def status(device_key: str):
    require_device_key(device_key)
    return {
        "live": time.monotonic() < live_until,
        "has_frame": latest_frame is not None,
        "last_frame_at": last_frame_at,
    }


@app.post("/api/live/frame")
async def upload_frame(device_key: str = Form(...), file: UploadFile = File(...)):
    global latest_frame, last_frame_at, live_until
    require_device_key(device_key)
    if file.content_type not in {"image/jpeg", "image/jpg", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Envie uma imagem JPEG.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Frame vazio.")
    latest_frame = content
    last_frame_at = time.time()
    live_until = time.monotonic() + LIVE_SECONDS
    frame_event.set()
    return {"ok": True, "bytes": len(content)}


async def mjpeg(request: Request):
    last_sent: bytes | None = None
    while not await request.is_disconnected():
        if latest_frame is not None and latest_frame != last_sent:
            last_sent = latest_frame
            yield (
                f"--{BOUNDARY}\r\n"
                "Content-Type: image/jpeg\r\n"
                f"Content-Length: {len(last_sent)}\r\n\r\n"
            ).encode() + last_sent + b"\r\n"
        try:
            await asyncio.wait_for(frame_event.wait(), timeout=1.0)
            frame_event.clear()
        except asyncio.TimeoutError:
            pass


@app.get("/api/live/stream/{device_key}")
async def stream(device_key: str, request: Request):
    require_device_key(device_key)
    return StreamingResponse(
        mjpeg(request),
        media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
        headers={"Cache-Control": "no-cache, no-store", "X-Accel-Buffering": "no"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
