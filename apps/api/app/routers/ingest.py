from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.db.models import User
from app.db.session import SessionLocal, get_db
from app.schemas import FacebookStreamStartRequest, IngestDemoRequest, ReplayStartRequest, TwitterStreamStartRequest
from app.services.ingestion import (
    create_post_and_queue,
    facebook_polling_status,
    ingest_facebook_once,
    ingest_twitter_once,
    start_facebook_polling,
    start_replay,
    start_twitter_polling,
    stop_facebook_polling,
    stop_replay,
    stop_twitter_polling,
    twitter_polling_status,
)

router = APIRouter(prefix="/ingest", tags=["ingest"])
settings = get_settings()


@router.post("/demo")
def ingest_demo(payload: IngestDemoRequest, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    post = create_post_and_queue(
        db=db,
        platform=payload.platform,
        platform_post_id=payload.platform_post_id,
        text=payload.text or "",
        author=payload.author or "demo_user",
        url=payload.url or "",
        raw_json=payload.raw_json,
        media_paths=payload.media_paths,
    )
    return {"ok": True, "post_id": post.id}


@router.post("/demo/upload")
async def ingest_demo_upload(json_file: UploadFile, media_file: UploadFile | None = None, _: User = Depends(get_current_user)):
    from app.core.config import get_settings

    settings = get_settings()
    demo_dir = Path(settings.demo_input_dir)
    demo_dir.mkdir(parents=True, exist_ok=True)
    json_path = demo_dir / json_file.filename
    json_path.write_bytes(await json_file.read())
    media_path = None
    if media_file is not None:
        media_path = demo_dir / media_file.filename
        media_path.write_bytes(await media_file.read())
    return {"ok": True, "json_path": str(json_path), "media_path": str(media_path) if media_path else None}


@router.post("/replay/start")
def replay_start(payload: ReplayStartRequest, _: User = Depends(get_current_user)):
    started = start_replay(SessionLocal, speed=payload.speed, limit=payload.limit)
    if not started:
        raise HTTPException(status_code=409, detail="Replay already running")
    return {"ok": True}


@router.post("/replay/stop")
def replay_stop(_: User = Depends(get_current_user)):
    stop_replay()
    return {"ok": True}


@router.post("/twitter/poll")
def ingest_from_twitter(
    query: str = settings.twitter_default_query,
    limit: int = 10,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if not settings.twitter_bearer_token:
        raise HTTPException(status_code=400, detail="TWITTER_BEARER_TOKEN is not configured")
    ingested = ingest_twitter_once(db=db, query=query, limit=limit)
    return {"ok": True, "ingested": ingested}


@router.post("/twitter/start")
def start_twitter_stream(payload: TwitterStreamStartRequest, _: User = Depends(get_current_user)):
    if not settings.twitter_bearer_token:
        raise HTTPException(status_code=400, detail="TWITTER_BEARER_TOKEN is not configured")
    query = payload.query or settings.twitter_default_query
    interval = max(10, payload.interval_sec)
    per_poll = min(100, max(1, payload.limit_per_poll))
    started = start_twitter_polling(SessionLocal, query=query, limit_per_poll=per_poll, interval_sec=interval)
    if not started:
        raise HTTPException(status_code=409, detail="Twitter polling already running")
    return {"ok": True, "query": query, "limit_per_poll": per_poll, "interval_sec": interval}


@router.post("/twitter/stop")
def stop_twitter_stream(_: User = Depends(get_current_user)):
    stop_twitter_polling()
    return {"ok": True}


@router.get("/twitter/status")
def twitter_status(_: User = Depends(get_current_user)):
    return twitter_polling_status()


def _configured_facebook_pages() -> list[str]:
    raw = settings.facebook_page_ids or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


@router.post("/facebook/poll")
def ingest_from_facebook(
    limit_per_page: int = 20,
    page_ids: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if not settings.facebook_page_access_token:
        raise HTTPException(status_code=400, detail="FACEBOOK_PAGE_ACCESS_TOKEN is not configured")
    pages = [p.strip() for p in (page_ids or "").split(",") if p.strip()] or _configured_facebook_pages()
    if not pages:
        raise HTTPException(status_code=400, detail="No Facebook page IDs configured")
    ingested = ingest_facebook_once(db=db, page_ids=pages, limit_per_page=min(100, max(1, limit_per_page)))
    return {"ok": True, "ingested": ingested, "page_ids": pages}


@router.post("/facebook/start")
def start_facebook_stream(payload: FacebookStreamStartRequest, _: User = Depends(get_current_user)):
    if not settings.facebook_page_access_token:
        raise HTTPException(status_code=400, detail="FACEBOOK_PAGE_ACCESS_TOKEN is not configured")
    pages = payload.page_ids or _configured_facebook_pages()
    if not pages:
        raise HTTPException(status_code=400, detail="No Facebook page IDs configured")
    interval = max(15, payload.interval_sec)
    per_page = min(100, max(1, payload.limit_per_page))
    started = start_facebook_polling(SessionLocal, page_ids=pages, limit_per_page=per_page, interval_sec=interval)
    if not started:
        raise HTTPException(status_code=409, detail="Facebook polling already running")
    return {"ok": True, "page_ids": pages, "limit_per_page": per_page, "interval_sec": interval}


@router.post("/facebook/stop")
def stop_facebook_stream(_: User = Depends(get_current_user)):
    stop_facebook_polling()
    return {"ok": True}


@router.get("/facebook/status")
def facebook_status(_: User = Depends(get_current_user)):
    return facebook_polling_status()
