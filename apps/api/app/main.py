import asyncio
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.routers import alerts, auth, debug, ingest, users, ws
from app.services.event_bus import subscribe_alerts
from app.services.ingestion import start_demo_folder_watcher
from app.services.ws_manager import ws_manager

settings = get_settings()


def _start_alert_subscription(loop: asyncio.AbstractEventLoop) -> None:
    def _on_message(payload: dict) -> None:
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast_json(payload), loop)

    def _run() -> None:
        import sys
        try:
            subscribe_alerts(_on_message)
        except Exception as e:
            print(f"[redis] Alert subscription stopped: {e}", file=sys.stderr, flush=True)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import sys
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[startup] DB create_all failed: {e}", file=sys.stderr, flush=True)
    try:
        Path(settings.media_root).mkdir(parents=True, exist_ok=True)
        Path(settings.demo_input_dir).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[startup] mkdir failed: {e}", file=sys.stderr, flush=True)
    try:
        loop = asyncio.get_running_loop()
        _start_alert_subscription(loop)
    except Exception as e:
        print(f"[startup] alert subscription failed: {e}", file=sys.stderr, flush=True)
    if settings.demo_mode:
        try:
            start_demo_folder_watcher(SessionLocal)
        except Exception as e:
            print(f"[startup] demo watcher failed: {e}", file=sys.stderr, flush=True)
    print("[startup] API ready", file=sys.stderr, flush=True)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(alerts.router)
app.include_router(ingest.router)
app.include_router(users.router)
app.include_router(debug.router)
app.include_router(ws.router)
# Ensure static mount directory exists at import time in cloud runtimes.
Path(settings.media_root).mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.media_root), name="storage")


@app.get("/health")
def health():
    return {"status": "ok"}
