import json
import shutil
import threading
import time
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlparse

import requests
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Media, Post
from app.workers.tasks import analyze_post_task

_replay_thread: Optional[threading.Thread] = None
_replay_stop = threading.Event()
_watcher_thread: Optional[threading.Thread] = None
_watcher_stop = threading.Event()
_processed_files: set[str] = set()
_twitter_thread: Optional[threading.Thread] = None
_twitter_stop = threading.Event()
_facebook_thread: Optional[threading.Thread] = None
_facebook_stop = threading.Event()


def _copy_media_to_storage(src: str, post_id: int) -> str:
    settings = get_settings()
    src_path = Path(src)
    if not src_path.exists():
        return src
    out_dir = Path(settings.media_root) / f"post_{post_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / src_path.name
    shutil.copy2(src_path, dst)
    return str(dst)


def create_post_and_queue(
    db: Session,
    platform: str,
    platform_post_id: str,
    text: str,
    author: str,
    url: str,
    raw_json: dict,
    media_paths: list[str],
) -> Post:
    post = Post(
        platform=platform,
        platform_post_id=platform_post_id,
        text=text,
        author=author,
        url=url,
        raw_json=raw_json,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    for path in media_paths:
        media_type = "video" if path.lower().endswith(".mp4") else "image"
        stored_path = _copy_media_to_storage(path, post.id)
        media = Media(post_id=post.id, type=media_type, path=stored_path, meta_json={})
        db.add(media)
    db.commit()

    analyze_post_task.delay(post.id)
    return post


def replay_dataset(db_factory, speed: float = 1.0, limit: int = 100) -> None:
    settings = get_settings()
    demo_dir = Path(settings.demo_input_dir)
    demo_dir.mkdir(parents=True, exist_ok=True)
    files = list(demo_dir.glob("*.json"))[:limit]

    for file_path in files:
        if _replay_stop.is_set():
            break
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        db = db_factory()
        try:
            create_post_and_queue(
                db=db,
                platform=payload.get("platform", "demo"),
                platform_post_id=payload.get("platform_post_id", file_path.stem),
                text=payload.get("text", ""),
                author=payload.get("author", "unknown"),
                url=payload.get("url", ""),
                raw_json=payload,
                media_paths=payload.get("media_paths", []),
            )
        finally:
            db.close()
        time.sleep(max(0.1, 1.0 / max(0.1, speed)))


def start_replay(db_factory, speed: float = 1.0, limit: int = 100) -> bool:
    global _replay_thread
    if _replay_thread and _replay_thread.is_alive():
        return False
    _replay_stop.clear()
    _replay_thread = threading.Thread(target=replay_dataset, args=(db_factory, speed, limit), daemon=True)
    _replay_thread.start()
    return True


def stop_replay() -> None:
    _replay_stop.set()


def poll_twitter_recent_search(query: str, limit: int = 10) -> Iterable[dict]:
    settings = get_settings()
    if not settings.twitter_bearer_token:
        return []
    headers = {"Authorization": f"Bearer {settings.twitter_bearer_token}"}
    params = {"query": query, "max_results": min(100, limit), "tweet.fields": "created_at,lang,author_id"}
    resp = requests.get("https://api.twitter.com/2/tweets/search/recent", headers=headers, params=params, timeout=20)
    if resp.status_code != 200:
        return []
    data = resp.json()
    return data.get("data", [])


def ingest_twitter_once(db: Session, query: str, limit: int = 10) -> int:
    tweets = list(poll_twitter_recent_search(query=query, limit=limit))
    ingested = 0
    for tweet in tweets:
        post_id = tweet.get("id")
        if not post_id:
            continue
        existing = db.query(Post).filter(Post.platform == "twitter", Post.platform_post_id == str(post_id)).first()
        if existing:
            continue
        create_post_and_queue(
            db=db,
            platform="twitter",
            platform_post_id=str(post_id),
            text=tweet.get("text", ""),
            author=str(tweet.get("author_id", "unknown")),
            url=f"https://x.com/i/web/status/{post_id}",
            raw_json=tweet,
            media_paths=[],
        )
        ingested += 1
    return ingested


def _watch_folder_loop(db_factory) -> None:
    settings = get_settings()
    demo_dir = Path(settings.demo_input_dir)
    demo_dir.mkdir(parents=True, exist_ok=True)
    while not _watcher_stop.is_set():
        for file_path in demo_dir.glob("*.json"):
            if file_path.name in _processed_files:
                continue
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
                media_paths = payload.get("media_paths", [])
                fixed_paths = []
                for path in media_paths:
                    p = Path(path)
                    if p.is_absolute():
                        fixed_paths.append(str(p))
                    else:
                        fixed_paths.append(str((demo_dir / p).resolve()))
                db = db_factory()
                try:
                    create_post_and_queue(
                        db=db,
                        platform=payload.get("platform", "demo"),
                        platform_post_id=payload.get("platform_post_id", file_path.stem),
                        text=payload.get("text", ""),
                        author=payload.get("author", "watcher"),
                        url=payload.get("url", ""),
                        raw_json=payload,
                        media_paths=fixed_paths,
                    )
                finally:
                    db.close()
                _processed_files.add(file_path.name)
            except Exception:
                continue
        time.sleep(2.0)


def start_demo_folder_watcher(db_factory) -> bool:
    global _watcher_thread
    if _watcher_thread and _watcher_thread.is_alive():
        return False
    _watcher_stop.clear()
    _watcher_thread = threading.Thread(target=_watch_folder_loop, args=(db_factory,), daemon=True)
    _watcher_thread.start()
    return True


def _twitter_poll_loop(db_factory, query: str, limit_per_poll: int, interval_sec: int) -> None:
    while not _twitter_stop.is_set():
        db = db_factory()
        try:
            ingest_twitter_once(db, query=query, limit=limit_per_poll)
        except Exception:
            pass
        finally:
            db.close()
        for _ in range(max(1, interval_sec)):
            if _twitter_stop.is_set():
                break
            time.sleep(1)


def start_twitter_polling(db_factory, query: str, limit_per_poll: int = 20, interval_sec: int = 30) -> bool:
    global _twitter_thread
    if _twitter_thread and _twitter_thread.is_alive():
        return False
    _twitter_stop.clear()
    _twitter_thread = threading.Thread(
        target=_twitter_poll_loop,
        args=(db_factory, query, limit_per_poll, interval_sec),
        daemon=True,
    )
    _twitter_thread.start()
    return True


def stop_twitter_polling() -> None:
    _twitter_stop.set()


def twitter_polling_status() -> dict:
    return {
        "running": bool(_twitter_thread and _twitter_thread.is_alive()),
    }


def poll_facebook_page_posts(page_id: str, limit: int = 20) -> Iterable[dict]:
    settings = get_settings()
    if not settings.facebook_page_access_token:
        return []
    endpoint = f"https://graph.facebook.com/v21.0/{page_id}/posts"
    params = {
        "access_token": settings.facebook_page_access_token,
        "fields": (
            "id,message,created_time,permalink_url,from,"
            "attachments{media_type,type,url,unshimmed_url,media,"
            "subattachments{media_type,type,url,unshimmed_url,media}}"
        ),
        "limit": min(100, max(1, limit)),
    }
    resp = requests.get(endpoint, params=params, timeout=20)
    if resp.status_code != 200:
        return []
    payload = resp.json()
    return payload.get("data", [])


def _iter_attachment_nodes(attachments_payload: dict) -> Iterable[dict]:
    for node in (attachments_payload or {}).get("data", []):
        yield node
        for child in (node.get("subattachments") or {}).get("data", []):
            yield child


def _first_http_url(candidates: list[object]) -> str:
    for candidate in candidates:
        value = str(candidate or "").strip()
        if value.startswith("http://") or value.startswith("https://"):
            return value
    return ""


def _facebook_media_urls(post: dict) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    attachments = post.get("attachments") or {}

    for node in _iter_attachment_nodes(attachments):
        media = node.get("media") or {}
        media_type = str(node.get("media_type") or node.get("type") or "").lower()
        image = media.get("image") or {}

        if "video" in media_type:
            candidate = _first_http_url(
                [
                    media.get("source"),
                    node.get("unshimmed_url"),
                    node.get("url"),
                ]
            )
        else:
            candidate = _first_http_url(
                [
                    image.get("src"),
                    media.get("source"),
                    node.get("unshimmed_url"),
                    node.get("url"),
                ]
            )

        if candidate and candidate not in seen:
            seen.add(candidate)
            urls.append(candidate)

    return urls


def _suffix_from_content_type(content_type: str) -> str:
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype == "video/mp4":
        return ".mp4"
    if ctype == "image/jpeg":
        return ".jpg"
    if ctype == "image/png":
        return ".png"
    if ctype == "image/webp":
        return ".webp"
    if ctype == "image/gif":
        return ".gif"
    if ctype.startswith("video/"):
        return ".mp4"
    if ctype.startswith("image/"):
        return ".jpg"
    return ""


def _download_remote_media(url: str, prefix: str) -> Optional[str]:
    settings = get_settings()
    try:
        resp = requests.get(url, timeout=30, stream=True, allow_redirects=True)
    except Exception:
        return None

    if resp.status_code != 200:
        return None

    content_type = (resp.headers.get("content-type") or "").lower()
    if not (content_type.startswith("video/") or content_type.startswith("image/")):
        return None

    parsed_suffix = Path(urlparse(resp.url).path).suffix.lower()
    allowed_suffixes = {".mp4", ".mov", ".m4v", ".jpg", ".jpeg", ".png", ".webp", ".gif"}
    suffix = parsed_suffix if parsed_suffix in allowed_suffixes else _suffix_from_content_type(content_type)
    if not suffix:
        return None

    tmp_dir = Path(settings.media_root) / "_ingest_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    safe_prefix = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in prefix)
    out_path = tmp_dir / f"{safe_prefix}_{int(time.time() * 1000)}{suffix}"

    try:
        with out_path.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if chunk:
                    fh.write(chunk)
    except Exception:
        return None

    return str(out_path)


def _facebook_media_paths(post: dict) -> list[str]:
    post_id = str(post.get("id", "post"))
    urls = _facebook_media_urls(post)
    paths: list[str] = []
    for idx, url in enumerate(urls):
        local_path = _download_remote_media(url, f"fb_{post_id}_{idx}")
        if local_path:
            paths.append(local_path)
    return paths


def ingest_facebook_once(db: Session, page_ids: list[str], limit_per_page: int = 20) -> int:
    ingested = 0
    for page_id in page_ids:
        posts = list(poll_facebook_page_posts(page_id=page_id, limit=limit_per_page))
        for post in posts:
            post_id = str(post.get("id", ""))
            if not post_id:
                continue
            existing = db.query(Post).filter(Post.platform == "facebook", Post.platform_post_id == post_id).first()
            if existing:
                continue
            create_post_and_queue(
                db=db,
                platform="facebook",
                platform_post_id=post_id,
                text=post.get("message", "") or "",
                author=str((post.get("from") or {}).get("name", page_id)),
                url=post.get("permalink_url", ""),
                raw_json=post,
                media_paths=_facebook_media_paths(post),
            )
            ingested += 1
    return ingested


def _facebook_poll_loop(db_factory, page_ids: list[str], limit_per_page: int, interval_sec: int) -> None:
    while not _facebook_stop.is_set():
        db = db_factory()
        try:
            ingest_facebook_once(db, page_ids=page_ids, limit_per_page=limit_per_page)
        except Exception:
            pass
        finally:
            db.close()
        for _ in range(max(1, interval_sec)):
            if _facebook_stop.is_set():
                break
            time.sleep(1)


def start_facebook_polling(db_factory, page_ids: list[str], limit_per_page: int = 20, interval_sec: int = 60) -> bool:
    global _facebook_thread
    if _facebook_thread and _facebook_thread.is_alive():
        return False
    _facebook_stop.clear()
    _facebook_thread = threading.Thread(
        target=_facebook_poll_loop,
        args=(db_factory, page_ids, limit_per_page, interval_sec),
        daemon=True,
    )
    _facebook_thread.start()
    return True


def stop_facebook_polling() -> None:
    _facebook_stop.set()


def facebook_polling_status() -> dict:
    return {"running": bool(_facebook_thread and _facebook_thread.is_alive())}
