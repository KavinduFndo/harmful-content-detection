from app.db.models import Post
from app.db.session import SessionLocal
from app.services.pipeline import run_analysis
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def analyze_post_task(self, post_id: int):
    db = SessionLocal()
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return {"ok": False, "reason": "post_not_found"}
        result = run_analysis(db, post)
        return {"ok": True, **result}
    finally:
        db.close()
