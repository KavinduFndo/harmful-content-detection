from celery import Celery
import ssl

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "harmful_content_detector",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Required for rediss:// (TLS) URLs: Celery/kombu need ssl_cert_reqs
_redis_use_ssl = settings.redis_url.strip().lower().startswith("rediss://")
_ssl_opts = {"ssl_cert_reqs": ssl.CERT_REQUIRED} if _redis_use_ssl else None

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=2,
    broker_use_ssl=_ssl_opts,
    redis_backend_use_ssl=_ssl_opts,
)

celery_app.autodiscover_tasks(["app.workers"])
