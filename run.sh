#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$ROOT_DIR/infra"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or not in PATH."
  echo "Install Docker Desktop for macOS, then re-run ./run.sh"
  echo "Download: https://www.docker.com/products/docker-desktop/"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin is not available."
  echo "Open Docker Desktop once and ensure Compose is enabled."
  exit 1
fi

echo "==> Starting Harmful Content Detector stack..."
cd "$INFRA_DIR"
docker compose up --build -d

echo "==> Waiting for API health at http://localhost:8000/health"
MAX_TRIES=60
TRIES=0
until curl -sSf "http://localhost:8000/health" >/dev/null 2>&1; do
  TRIES=$((TRIES + 1))
  if [ "$TRIES" -ge "$MAX_TRIES" ]; then
    echo "API did not become healthy in time. Check logs:"
    echo "  cd \"$INFRA_DIR\" && docker compose logs -f api"
    exit 1
  fi
  sleep 2
done

echo "==> API is healthy. Seeding admin user..."
cd "$INFRA_DIR"
docker compose exec -T api python - <<'PY'
from datetime import datetime

from app.core.security import hash_password
from app.db.models import User, UserRole
from app.db.session import SessionLocal

email = "admin@example.com"
password = "admin12345"

db = SessionLocal()
try:
    user = db.query(User).filter(User.email == email).first()
    if user:
        print(f"Admin already exists: {email}")
    else:
        db.add(
            User(
                email=email,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                created_at=datetime.utcnow(),
            )
        )
        db.commit()
        print(f"Seeded admin user: {email}")
finally:
    db.close()
PY

echo
echo "==> Stack is up"
echo "Web: http://localhost:5173"
echo "API: http://localhost:8000"
echo
echo "Default admin:"
echo "  email:    admin@example.com"
echo "  password: admin12345"
echo
echo "Useful commands:"
echo "  ./stop.sh                         # stop all services"
echo "  cd infra && docker compose logs -f api"
echo "  cd infra && docker compose logs -f worker"
