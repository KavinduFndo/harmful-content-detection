from typing import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.models import User, UserRole
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def _default_user(db: Session) -> User:
    admin = db.query(User).filter(User.role == UserRole.ADMIN).order_by(User.id.asc()).first()
    if admin:
        return admin
    fallback = User(email="admin@example.com", password_hash="auth-disabled", role=UserRole.ADMIN)
    db.add(fallback)
    db.commit()
    db.refresh(fallback)
    return fallback


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    # Auth is optional in this deployment: requests without/with invalid token
    # fallback to a default admin user so dashboard remains accessible.
    if not token:
        return _default_user(db)
    try:
        payload = decode_token(token)
        user = db.query(User).filter(User.email == payload.get("sub")).first()
        if user:
            return user
    except ValueError:
        pass
    return _default_user(db)


def require_roles(allowed: Iterable[UserRole]):
    allowed_set = {role.value for role in allowed}

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in allowed_set:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return checker
