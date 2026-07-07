# Milking Process Compliance Monitor

Computer-vision pipeline that monitors milking staff compliance. A FastAPI inference service reads an RTSP camera feed via go2rtc, runs YOLOv8 detection, and uses a state machine to infer milking task events. A Next.js supervisor dashboard provides scheduling, live monitoring, analytics, and reporting.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Camera     │────▶│   go2rtc     │────▶│  Next.js Web App │
│  (RTSP)      │     │  (port 1984) │     │  (port 3000)     │
└──────────────┘     └──────┬───────┘     └────────┬─────────┘
                            │                       │
                            │ RTSP                  │ HTTP POST
                            ▼                       ▼
                     ┌──────────────┐     ┌──────────────────┐
                     │  Inference   │────▶│   PostgreSQL     │
                     │  Service     │     │   (port 5432)    │
                     │  (port 8001) │     └──────────────────┘
                     └──────────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| **PostgreSQL** | 5432 | Database for sessions, tasks, audit logs |
| **go2rtc** | 1984, 8554, 8555 | RTSP camera restreaming, WebRTC for browser |
| **Web App** | 3000 | Next.js 15 supervisor dashboard |
| **Inference Service** | 8001 | FastAPI + YOLOv8 detection pipeline |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Project-Mzariaa-0/Monitoring_Platform-v1.git
cd Monitoring_Platform-v1/Monitoring_App/milking-monitor
```

### 2. Configure environment

Create a `.env` file in the project root (`Monitoring_App/milking-monitor/`):

```env
POSTGRES_DB=milking_monitor
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-secure-password
```

Create `apps/web/.env.local`:

```env
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret
AUTH_SECRET=your-auth-secret
DATABASE_URL=postgres://postgres:your-secure-password@localhost:5432/milking_monitor
INFERENCE_SERVICE_TOKEN=inference-secret-token
GO2RTC_URL=http://localhost:1984
```

Create `apps/inference-service/.env`:

```env
RTSP_STREAM_URL=rtsp://admin:password@camera-ip:554/Streaming/Channels/101
WEB_APP_INGEST_URL=http://localhost:3000/api/events/ingest
WEB_APP_INGEST_TOKEN=inference-secret-token
MODEL_WEIGHTS_PATH=yolov8n.pt
CORS_ORIGINS=http://localhost:3000
```

Create `apps/go2rtc/go2rtc.yaml`:

```yaml
api:
  listen: ":1984"
  origin: "*"

streams:
  camera1: rtsp://admin:password@camera-ip:554/Streaming/Channels/101
  camera2: rtsp://admin:password@camera-ip:554/Streaming/Channels/102

webrtc:
  listen: ":8555"
  candidates:
    - stun:8555
```

### 3. Start all services

```bash
docker compose up -d
```

### 4. Verify services

```bash
# Check all containers are running
docker compose ps

# Test PostgreSQL
docker compose exec postgres pg_isready -U postgres

# Test go2rtc
curl http://localhost:1984/api/streams

# Test inference service
curl http://localhost:8001/

# Test web app
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/
```

### 5. Open the dashboard

```
http://localhost:3000
```

## Service Details

### PostgreSQL

- **Image**: `postgres:16`
- **Port**: 5432
- **Volume**: `postgres_data` (persists across restarts)
- **Health check**: `pg_isready -U postgres`

### go2rtc

- **Image**: `alexxit/go2rtc`
- **Ports**: 1984 (API), 8554 (RTSP), 8555 (WebRTC)
- **Config**: `apps/go2rtc/go2rtc.yaml`
- **Purpose**: Receives RTSP camera streams and restreams them to the browser via WebRTC
- **Built-in UI**: `http://localhost:1984` (for debugging streams)
- **API**: `http://localhost:1984/api/streams` (list configured streams)

### Web App (Next.js)

- **Framework**: Next.js 15 (App Router)
- **Port**: 3000
- **Auth**: NextAuth v4 (Credentials + Email via Resend)
- **Database**: PostgreSQL via Drizzle ORM
- **Realtime**: Server-Sent Events via `/api/ws`
- **Styling**: Vanilla CSS with Cooperative design tokens

**Key pages:**
| Route | Description |
|-------|-------------|
| `/` | Dashboard overview with live camera feeds |
| `/live` | Real-time monitoring with task status per cow position |
| `/analytics` | Compliance scores, missed tasks, efficiency |
| `/logs` | Audit trail with severity filters |
| `/equipment` | System service status |
| `/scheduler` | Session list and creation |
| `/scheduler/new` | Multi-step session creation form |
| `/sessions/[id]` | Session detail with task events |

**Key API routes:**
| Route | Method | Description |
|-------|--------|-------------|
| `/api/sessions` | GET/POST | List or create sessions |
| `/api/events/ingest` | POST | Inference service pushes events (Bearer token auth) |
| `/api/task-events/[id]/override` | POST | Supervisor overrides task status |
| `/api/reports/generate` | POST | Generate DOCX compliance report |
| `/api/ws` | GET | SSE real-time event stream |
| `/api/go2rtc` | GET | Proxy to query go2rtc stream info |

### Inference Service (FastAPI)

- **Framework**: FastAPI (Python 3.12)
- **Port**: 8001
- **ML Model**: YOLOv8 (Ultralytics)
- **Video**: OpenCV (headless)

**Key endpoints:**
| Endpoint | Description |
|----------|-------------|
| `GET /` | Health check |
| `GET /active-sessions` | List running inference sessions |
| `POST /session-window` | Start inference for a session |
| `POST /session-window/{id}/stop` | Stop a running session |
| `POST /test-send` | Send fake events to test pipeline |

**Pipeline**: RTSP → ROI Split → YOLOv8 → State Machine → HTTP POST to web app

## Milking Tasks

The system detects 6 sequential milking tasks per cow position:

| Task | Name | Detection Signal |
|------|------|-----------------|
| TASK-01 | Pre-cleaning | `person` + `spray_bottle` |
| TASK-02 | Stripping | `person` + `stripping_cup` |
| TASK-03 | Machine attachment | `teat_cups_attached` |
| TASK-04 | Milking (active) | `teat_cups_attached` |
| TASK-05 | Detachment | `teat_cups_detached` |
| TASK-06 | Post-dip | `person` + `dip_applicator` |

> **Note**: Currently uses COCO-pretrained YOLOv8 which only detects `person`. Custom model training is required for milking-specific classes.

## Camera Setup

The inference service needs an RTSP camera stream. For detailed setup instructions, see **[docs/PORT-FORWARDING.md](docs/PORT-FORWARDING.md)**.

**Quick summary:**
1. Find the camera's local IP (from HikConnect app → Device Details → Network Settings)
2. Port forward port 554 on the router to the camera's local IP
3. Use the router's public IP in the config files

## Development

### Run without Docker

**Web App:**
```bash
cd apps/web
npm install
npm run dev
```

**Inference Service:**
```bash
cd apps/inference-service
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

### Testing

```bash
# Web app tests
cd apps/web
npx vitest run

# Inference service tests
cd apps/inference-service
pytest tests/ -v

# Lint
cd apps/web && npx next lint
cd apps/inference-service && ruff check src/
```

### Build

```bash
cd apps/web
npx next build
```

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on push to `main`/`dev` and PRs:

| Job | Checks |
|-----|--------|
| **web-checks** | TypeScript, ESLint, Next.js build, Vitest |
| **inference-checks** | Ruff lint, Pytest |
| **integration-checks** | Docker Compose smoke test |

## Project Structure

```
milking-monitor/
├── apps/
│   ├── web/                          # Next.js supervisor dashboard
│   │   ├── app/
│   │   │   ├── (dashboard)/          # Dashboard pages (19 pages)
│   │   │   ├── api/                  # API routes (7 routes)
│   │   │   ├── sign-in/              # Auth pages
│   │   │   └── sign-up/
│   │   ├── components/
│   │   │   ├── dashboard/            # Dashboard components
│   │   │   ├── ui/                   # SealRing, StatusTag
│   │   │   ├── layout/               # DashboardShell
│   │   │   └── forms/                # Multi-step form
│   │   ├── lib/
│   │   │   ├── data/store.ts         # Database access (649 lines)
│   │   │   ├── db/schema/            # Drizzle ORM schemas
│   │   │   ├── constants.ts          # Task labels, scoring
│   │   │   ├── security/             # Rate limiting, sanitization
│   │   │   └── auth/                 # NextAuth config
│   │   └── app/globals.css           # Design tokens (756 lines)
│   │
│   ├── inference-service/            # FastAPI + YOLOv8
│   │   ├── src/
│   │   │   ├── main.py               # FastAPI app, endpoints
│   │   │   ├── runtime/              # Session runner (5 FPS)
│   │   │   ├── detection/            # YOLOv8 wrapper
│   │   │   ├── ingestion/            # RTSP reader, ROI splitter
│   │   │   ├── state_machine/        # Task FSM, cow process
│   │   │   ├── events/               # Event builder, publisher
│   │   │   └── config/               # ROIs, thresholds
│   │   └── tests/                    # 19 pytest tests
│   │
│   └── go2rtc/                       # go2rtc config
│       └── go2rtc.yaml
│
├── agent_plans/                      # Planning docs, technical reference
├── docker-compose.yml                # All 4 services
└── .github/workflows/ci.yml         # CI/CD pipeline
```

## Environment Variables

### Root `.env`
| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_DB` | No | Database name (default: `milking_monitor`) |
| `POSTGRES_USER` | No | Postgres user (default: `postgres`) |
| `POSTGRES_PASSWORD` | Yes | Postgres password |

### `apps/web/.env.local`
| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `AUTH_SECRET` | Yes | NextAuth secret |
| `NEXTAUTH_SECRET` | Yes | NextAuth secret |
| `NEXTAUTH_URL` | Yes | Base URL (e.g. `http://localhost:3000`) |
| `INFERENCE_SERVICE_TOKEN` | Yes | Bearer token for event ingestion |
| `GO2RTC_URL` | No | go2rtc API URL (default: `http://localhost:1984`) |
| `RESEND_API_KEY` | No | Resend API key for email |

### `apps/inference-service/.env`
| Variable | Required | Description |
|----------|----------|-------------|
| `RTSP_STREAM_URL` | Yes | Camera RTSP stream URL |
| `WEB_APP_INGEST_URL` | Yes | Web app ingest endpoint |
| `WEB_APP_INGEST_TOKEN` | Yes | Bearer token (must match `INFERENCE_SERVICE_TOKEN`) |
| `MODEL_WEIGHTS_PATH` | No | YOLOv8 weights (default: `yolov8n.pt`) |
| `CORS_ORIGINS` | No | CORS origins (default: `http://localhost:3000`) |

## Known Limitations

- **YOLO model**: COCO pretrained only — detects `person` but not milking-specific classes. Custom training required.
- **2 cow positions**: Camera covers only 2 positions. Full-row coverage is Phase 2.
- **Single camera angle**: Side view causes occlusion. Verifies task occurrence, not quality.
- **In-memory state**: Rate limiting and SSE don't survive restarts.
