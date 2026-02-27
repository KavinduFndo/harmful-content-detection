import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

sys.path.append(str((Path(__file__).resolve().parents[1] / "apps" / "api").resolve()))

from app.db.models import User, UserRole
from app.core.security import hash_password


def main() -> None:
    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://hcd_user:hcd_password@localhost:5432/harmful_content")
    email = os.getenv("SEED_ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("SEED_ADMIN_PASSWORD", "admin12345")
    role = UserRole.ADMIN

    engine = create_engine(db_url, future=True)
    session_factory = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False)
    db = session_factory()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"Admin already exists: {email}")
            return
        user = User(email=email, password_hash=hash_password(password), role=role, created_at=datetime.utcnow())
        db.add(user)
        db.commit()
        print(f"Seeded admin user: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
