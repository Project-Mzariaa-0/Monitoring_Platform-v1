# Inference Service

Real-time milking compliance monitoring service. Reads an RTSP camera feed, runs YOLOv8 object detection per frame, and uses a rule-based state machine to infer milking task completion/missed events. Publishes events to the Next.js web app backend.

## Architecture

```
Camera (RTSP)
     │
     ▼
┌─────────────────────────────────────────────────┐
│              Inference Service                   │
│                                                  │
│  RtspReader ──► ROI Splitter ──► YoloDetector   │
│       │              │                │          │
│       │         cow_position     Detection[]     │
│       │         1 and 2               │          │
│       │                              ▼          │
│       │                    ┌─────────────────┐  │
│       │                    │  State Machine   │  │
│       │                    │                  │  │
│       │                    │  CowProcess      │  │
│       │                    │  Boundary        │  │
│       │                    │       +          │  │
│       │                    │  TaskStateMachine│  │
│       │                    │  (6-task FSM)    │  │
│       │                    └────────┬────────┘  │
│       │                             │           │
│       │                        Event[]          │
│       │                             │           │
│       │                             ▼           │
│       │                    ┌─────────────────┐  │
│       │                    │ EventPublisher   │  │
│       │                    │ (HTTP POST x3)   │  │
│       │                    └────────┬────────┘  │
└─────────────────────────────────────┼───────────┘
                                      │
                                      ▼
                          Next.js /api/events/ingest
                                      │
                                      ▼
                               PostgreSQL + SSE
                                      │
                                      ▼
                            Supervisor Dashboard
```

## Quick Start

### Prerequisites

- Python 3.12+
- Camera with RTSP stream (or test stream)
- Next.js web app running on port 3000

### 1. Install dependencies

```bash
cd apps/inference-service
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
RTSP_STREAM_URL=rtsp://localhost:8554/stream
WEB_APP_INGEST_URL=http://localhost:3000/api/events/ingest
WEB_APP_INGEST_TOKEN=your-ingest-token-here
MODEL_WEIGHTS_PATH=yolov8n.pt
CORS_ORIGINS=http://localhost:3000
```

### 3. Start the service

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

### 4. Verify it's running

```bash
curl http://localhost:8001/
# {"status":"ok"}
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check — returns `{"status": "ok"}` |
| `GET` | `/active-sessions` | List currently running session IDs |
| `POST` | `/session-window` | Start inference for a session |
| `POST` | `/session-window/{session_id}/stop` | Stop a running session |
| `POST` | `/test-send` | Send fake events to test the full pipeline |

### Start a session

```bash
curl -X POST http://localhost:8001/session-window \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-001",
    "start_time": "2026-07-03T12:00:00Z",
    "end_time": "2026-07-03T13:00:00Z",
    "cow_positions": [1, 2]
  }'
```

Response: `{"status": "processing", "session_id": "session-001"}`

### Test the pipeline (no camera needed)

```bash
curl -X POST http://localhost:8001/test-send \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "start_time": "2026-07-03T12:00:00Z",
    "end_time": "2026-07-03T13:00:00Z"
  }'
```

Sends 6 synthetic task events (TASK-01 through TASK-06) to the web app ingest endpoint. Useful for verifying the full pipeline without a camera.

## How It Works

### Frame Pipeline

1. **RTSP Reader** (`src/ingestion/rtsp_reader.py`) — Opens the camera stream via OpenCV, yields `(frame_index, frame)` tuples.

2. **ROI Splitter** (`src/ingestion/roi_splitter.py`) — Crops each frame into two regions of interest (one per cow position) using coordinates from `src/config/rois.json`.

3. **YOLO Detector** (`src/detection/yolo_detector.py`) — Runs YOLOv8 inference on each ROI, returns `Detection` objects with `class_name`, `confidence`, and `bbox`.

4. **State Machine** — Two parallel processors consume detections:
   - **Cow Process Boundary** (`src/state_machine/cow_process_boundary.py`) — Tracks when a cow enters/leaves the milking process (started/completed).
   - **Task State Machine** (`src/state_machine/task_state_machine.py`) — Maps YOLO class names to the 6 milking tasks, tracks completion/missed status.

5. **Event Publisher** (`src/events/publisher.py`) — POSTs events to the Next.js backend with 3-attempt retry. Never crashes the session thread — logs and drops on failure.

### Frame Rate

The pipeline targets **5 FPS** (configurable via `TARGET_FPS` in `session_runner.py`). Each loop iteration:
- Reads a frame
- Splits into ROIs
- Runs detection
- Processes state machines
- Sleeps for remaining frame interval

### Task Detection Signals

Each task is triggered when **all** required YOLO classes are detected in the same ROI frame:

| Task | Name | Required Detections |
|------|------|-------------------|
| TASK-01 | Pre-milking cleaning | `person` + `spray_bottle` |
| TASK-02 | Stripping | `person` + `stripping_cup` |
| TASK-03 | Machine attachment | `teat_cups_attached` |
| TASK-04 | Milking (active) | `teat_cups_attached` |
| TASK-05 | Machine detachment | `teat_cups_detached` |
| TASK-06 | Post-dip application | `person` + `dip_applicator` |

### Confidence Thresholds

Per-task confidence thresholds are defined in `src/config/thresholds.json`:

```json
{
  "default_missed_task_seconds": 180,
  "default_unverifiable_confidence": 0.5,
  "default_completeness_confidence": 0.7,
  "TASK-01": { "confidence": 0.82 },
  "TASK-02": { "confidence": 0.78 },
  "TASK-03": { "confidence": 0.96 },
  "TASK-04": { "confidence": 0.91 },
  "TASK-05": { "confidence": 0.95 },
  "TASK-06": { "confidence": 0.80 }
}
```

### ROI Configuration

Camera regions of interest are defined in `src/config/rois.json`:

```json
{
  "cow_position_1": { "x": 0, "y": 0, "width": 640, "height": 720 },
  "cow_position_2": { "x": 640, "y": 0, "width": 640, "height": 720 }
}
```

Adjust these values to match your camera's field of view and cow positions.

## Docker

Run via docker compose from the project root:

```bash
docker compose up inference-service
```

The service starts on port 8001 and reads config from `.env`.

## Testing

### Run all tests

```bash
pytest tests/ -v
```

### Run by category

```bash
# Unit tests (no external dependencies)
pytest tests/unit/ -v

# API endpoint tests
pytest tests/api/ -v

# Integration tests (event contracts)
pytest tests/integration/ -v
```

### Test structure

```
tests/
├── conftest.py                    # Shared fixtures (TestClient, sample data)
├── api/
│   └── test_health.py             # 4 tests: health, sessions, 404, 400
├── integration/
│   └── test_event_contract.py     # 4 tests: event builder contracts
└── unit/
    ├── test_roi_splitter.py       # 4 tests: frame splitting, cropping
    └── test_task_state_machine.py # 7 tests: signals, dedup, duration
```

### Linting

```bash
ruff check src/
ruff format src/
```

## Project Structure

```
inference-service/
├── .env.example              # Environment variable template
├── pyproject.toml            # Project config (pytest, ruff)
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Dev dependencies
├── src/
│   ├── main.py               # FastAPI app, endpoints, session management
│   ├── config/
│   │   ├── rois.json         # Camera region-of-interest coordinates
│   │   └── thresholds.json   # Per-task confidence thresholds
│   ├── detection/
│   │   └── yolo_detector.py  # YOLOv8 inference wrapper
│   ├── events/
│   │   ├── event_builder.py  # Build task/cow_process event payloads
│   │   └── publisher.py      # HTTP POST publisher with retry
│   ├── ingestion/
│   │   ├── roi_splitter.py   # Crop frame into ROI regions
│   │   └── rtsp_reader.py    # OpenCV RTSP stream reader
│   ├── runtime/
│   │   └── session_runner.py # Main pipeline loop (5 FPS)
│   └── state_machine/
│       ├── cow_process_boundary.py   # Cow process start/end detection
│       └── task_state_machine.py     # 6-task finite state machine
└── tests/
    ├── conftest.py
    ├── api/
    ├── integration/
    └── unit/
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RTSP_STREAM_URL` | Yes | — | RTSP stream URL for the camera |
| `WEB_APP_INGEST_URL` | Yes | — | Next.js `/api/events/ingest` endpoint |
| `WEB_APP_INGEST_TOKEN` | Yes | — | Bearer token for ingest authentication |
| `MODEL_WEIGHTS_PATH` | No | `yolov8n.pt` | Path to YOLOv8 weights file |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated allowed CORS origins |

## Current Limitations

- **YOLO model**: Currently uses COCO-pretrained `yolov8n.pt` which detects `person` but not milking-specific classes (`spray_bottle`, `stripping_cup`, `teat_cups_attached`, `teat_cups_detached`, `dip_applicator`). Custom model training is required.
- **2 cow positions**: Camera covers only the first 2 cow positions. Full-row coverage is a Phase 2 item.
- **Single camera angle**: Side view causes occlusion during close-contact tasks. System verifies task occurrence/duration, not execution quality.
- **In-memory state**: Rate limiting and active session tracking don't survive restarts.

## Next Steps

1. **Custom YOLOv8 model training** — Collect labeled data for milking-specific classes, train on domain data
2. **Additional cameras** — Cover more cow positions, reduce occlusion
3. **Temporal model** — Replace/augment rule-based state machine with learned model (Phase 2)
4. **Redis queue** — Replace in-memory event publishing with durable queue for reliability
