# Harmful Content Detector

Production-style monorepo for a bilingual (Sinhala + English), multimodal, real-time harmful social content detection system.

## Features

- Real-time ingestion from:
  - Demo mode folder watcher (`data/demo_inputs/*.json`)
  - Demo replay stream (`POST /ingest/replay/start`)
  - Optional Twitter/X polling (`POST /ingest/twitter/poll`) via bearer token
  - Stub adapters for YouTube, Facebook, TikTok
- Two-stage detection pipeline:
  - Keyword prefilter in Sinhala and English
  - Multimodal inference:
    - Text classifier wrapper (supports local `.pt` or HF folder; fallback heuristic)
    - Video inference via YOLO (`.pt` weights)
    - Audio transcript via Whisper + NLP scoring of transcript
- Fusion engine with configurable weighted scores and severity mapping
- Alert creation and real-time WebSocket broadcast
- Evidence persistence (post metadata, media, transcript path, evidence frame paths)
- JWT auth + RBAC (`ADMIN`, `MODERATOR`, `POLICE`)
- React dashboard for moderation and review workflow
  - Includes ADMIN-only debug console for model checks

## Monorepo Structure

```text
harmful-content-detector/
  apps/
    api/
    web/
  packages/
    shared/
  infra/
    docker-compose.yml
  models/
    yolo/weights.pt
    nlp/
  data/
    keywords/
    demo_inputs/
  scripts/
  README.md
```

## Environment

Copy/edit `.env` if needed:

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `DEMO_MODE=true`
- `TWITTER_BEARER_TOKEN` (optional)
- `YOLO_WEIGHTS_PATH`
- `NLP_MODEL_PATH`
- `NLP_ADAPTER_PATH` (optional custom Python adapter)
- `NLP_LABEL_MAP_JSON` (optional class index mapping)
- `WHISPER_MODEL`
- `VIOLENCE_CLASS_KEYWORDS`
- `FUSION_TEXT_W`, `FUSION_VIDEO_W`, `FUSION_AUDIO_W`
- `ALERT_THRESHOLD`

## Run with Docker

From `harmful-content-detector/infra`:

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Web: `http://localhost:5173`
- Postgres: `localhost:5432`
- Redis: `localhost:6379`

### One-command run

From `harmful-content-detector/`:

```bash
./run.sh
```

To stop:

```bash
./stop.sh
```

## Seed Admin User

In a separate shell:

```bash
cd harmful-content-detector
python scripts/seed_db.py
```

Default credentials:

- Email: `admin@example.com`
- Password: `admin12345`

## Demo Flow

1. Sign in on web dashboard.
2. Ingest demo data:
   - Folder watcher auto-ingests files dropped in `data/demo_inputs/`
   - Or call `POST /ingest/replay/start` to replay local dataset
3. Worker runs analysis and creates alerts for high-risk posts.
4. New alerts appear instantly in Alerts page through WebSocket.

## End-to-End Verification Commands

Use these after stack is up and admin is seeded:

```bash
# 1) Login and capture JWT
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin12345"}' | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2) Start replay
curl -s -X POST http://localhost:8000/ingest/replay/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"speed":1.5,"limit":50}'

# 3) List alerts
curl -s "http://localhost:8000/alerts?page=1&limit=20" \
  -H "Authorization: Bearer $TOKEN"

# 4) Run model check (text only)
curl -s -X POST http://localhost:8000/debug/model-check \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"He said he will kill with a gun tonight","lang":"en"}'
```

## API Endpoints

- Auth:
  - `POST /auth/login`
  - `POST /auth/register` (ADMIN)
  - `GET /auth/me`
- Alerts:
  - `GET /alerts`
  - `GET /alerts/{id}`
  - `PATCH /alerts/{id}`
  - `POST /alerts/{id}/feedback`
- Ingestion:
  - `POST /ingest/demo`
  - `POST /ingest/demo/upload`
  - `POST /ingest/replay/start`
  - `POST /ingest/replay/stop`
  - `POST /ingest/twitter/poll`
  - `POST /ingest/twitter/start`
  - `POST /ingest/twitter/stop`
  - `GET /ingest/twitter/status`
  - `POST /ingest/facebook/poll`
  - `POST /ingest/facebook/start`
  - `POST /ingest/facebook/stop`
  - `GET /ingest/facebook/status`
- Debug:
  - `POST /debug/model-check` (ADMIN only)
- WebSocket:
  - `WS /ws/alerts`

## Tests

Run backend unit tests:

```bash
cd harmful-content-detector/apps/api
pytest -q
```

Included tests:

- Fusion scoring logic
- Keyword prefilter matching
- Auth security helpers (hash and JWT)

## Notes on Trained Models

- Place YOLO weights at `models/yolo/weights.pt` (or update env path)
- Place NLP model in `models/nlp/` or provide `.pt` file path via `NLP_MODEL_PATH`
- Optional custom NLP integration: implement `models/nlp/infer.py` with:
  - `predict(text: str, lang: str, categories: list[str]) -> dict[str, float]`
- Optional class index mapping:
  - Add `models/nlp/label_map.json` like `{"0":"harassment_hate_speech","1":"general_violence"}`
  - Or set `NLP_LABEL_MAP_JSON` in env
- YOLO detections are filtered by `VIOLENCE_CLASS_KEYWORDS`
- If model loading fails, system falls back to deterministic heuristic mode so demo still runs

## Real Social Posts (Twitter/X)

1. Set `TWITTER_BEARER_TOKEN` in `.env` (X developer app bearer token).
2. Restart services:

```bash
cd infra
docker compose up --build -d
```

3. Login and get token:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin12345"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

4. One-time fetch:

```bash
curl -s -X POST "http://localhost:8000/ingest/twitter/poll?limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

5. Continuous real-time polling:

```bash
curl -s -X POST http://localhost:8000/ingest/twitter/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"(violence OR murder OR abuse OR hate speech) (lang:en OR lang:si)","limit_per_poll":20,"interval_sec":30}'
```

6. Check status:

```bash
curl -s http://localhost:8000/ingest/twitter/status -H "Authorization: Bearer $TOKEN"
```

7. Stop polling:

```bash
curl -s -X POST http://localhost:8000/ingest/twitter/stop -H "Authorization: Bearer $TOKEN"
```

## Real Social Posts (Facebook - Primary)

Important: this connector uses Meta Graph API for **Facebook Pages**.  
It does not read private profiles/groups without approved permissions.

1. Set these in `.env`:

```env
FACEBOOK_PAGE_ACCESS_TOKEN=YOUR_PAGE_ACCESS_TOKEN
FACEBOOK_PAGE_IDS=PAGE_ID_1,PAGE_ID_2
```

2. Restart API + worker:

```bash
cd infra
docker compose up --build -d api worker
```

3. One-time fetch from configured pages:

```bash
curl -s -X POST "http://localhost:8000/ingest/facebook/poll?limit_per_page=20" \
  -H "Authorization: Bearer $TOKEN"
```

4. Continuous polling (recommended):

```bash
curl -s -X POST http://localhost:8000/ingest/facebook/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"limit_per_page":20,"interval_sec":60}'
```

5. Check status / stop:

```bash
curl -s http://localhost:8000/ingest/facebook/status -H "Authorization: Bearer $TOKEN"
curl -s -X POST http://localhost:8000/ingest/facebook/stop -H "Authorization: Bearer $TOKEN"
```

## Screenshots

- `docs/screenshots/login.png` (placeholder)
- `docs/screenshots/alerts-list.png` (placeholder)
- `docs/screenshots/alert-detail.png` (placeholder)
