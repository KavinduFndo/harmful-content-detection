#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$ROOT_DIR/infra"

echo "==> Stopping Harmful Content Detector stack..."
cd "$INFRA_DIR"
docker compose down
echo "==> Stopped."
