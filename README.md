<div align="center">

# Milking Monitor

**Real-time compliance monitoring platform for dairy farming operations**

Computer vision (YOLO + LSTM) from RTSP camera streams + a Next.js web interface for continuous monitoring and compliance tracking.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-18+-339933?style=flat-square&logo=node.js&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-inference-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-frontend-000000?style=flat-square&logo=next.js&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-database-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-model-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)
![License](https://img.shields.io/badge/license-Commercial-red?style=flat-square)

</div>

---

## Table of Contents

- [Project Overview](#project-overview)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [AI Model Architecture](#ai-model-architecture)
- [API Endpoints](#api-endpoints)
- [Business Logic](#business-logic)
- [Real-Time Event Flow](#real-time-event-flow)
- [Dashboard Features](#dashboard-features)
- [Security & Authentication](#security--authentication)
- [Development & Testing](#development--testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)
- [License](#license)

---

## Project Overview

A cooperative dairy milking compliance monitoring platform that:

1. **Detects milking tasks** in real-time using a multimodal AI model (YOLOv8-Pose + YOLOv8n + LSTM)
2. **Tracks compliance** against the 6-step milking protocol
3. **Streams live data** to a web dashboard via Server-Sent Events
4. **Generates reports** (PDF/DOCX) for compliance auditing

### Key Features

- **Multimodal AI**: Pose estimation + object detection + temporal LSTM for task recognition
- **Live Dashboard**: Real-time task status, compliance scores, and session management
- **Cooperative Design**: Multi-organization support with role-based access
- **CI/CD**: Automated testing and deployment via GitHub Actions
- **Camera Integration**: RTSP streaming via go2rtc with WebRTC support

---

## Project Structure

```
Monitoring_Platform-v1/
├── Monitoring_App/milking-monitor/apps/
│   ├── inference-service/              # Python FastAPI backend
│   │   ├── src/
│   │   │   ├── main.py                # FastAPI application + session management
│   │   │   ├── detection/
│   │   │   │   ├── hybrid_detector.py          # Multimodal LSTM detector
│   │   │   │   ├── multimodal_feature_extractor.py  # Pose + object features
│   │   │   │   ├── pose_feature_extractor.py   # YOLOv8-Pose (512 dims)
│   │   │   │   └── object_feature_extractor.py # YOLOv8n (128 dims)
│   │   │   ├── runtime/
│   │   │   │   └── session_runner.py  # Session lifecycle + task detection
│   │   │   ├── ingestion/
│   │   │   │   └── rtsp_reader.py     # Camera/video stream processing
│   │   │   ├── state_machine/
│   │   │   │   └── task_state_machine.py  # Task progression rules
│   │   │   └── events/
│   │   │       └── publisher.py       # Event delivery to web app
│   │   ├── models/checkpoints/        # Trained LSTM weights
│   │   └── requirements.txt
│   │
│   ├── web/                           # Next.js frontend
│   │   ├── app/
│   │   │   ├── (dashboard)/
│   │   │   │   ├── page.tsx           # Main dashboard
│   │   │   │   ├── live/page.tsx      # Live session view
│   │   │   │   ├── sessions/          # Session history + detail
│   │   │   │   └── reports/           # Report generation
│   │   │   └── api/                   # API routes
│   │   ├── components/                # React components
│   │   ├── lib/                       # Data access, auth, utilities
│   │   └── public/                    # Static assets (fallback.mp4)
│   │
│   └── go2rtc/                        # Camera streaming (Docker)
│       └── go2rtc.yaml
│
├── hybrid-model/                      # AI model training
│   ├── src/
│   │   ├── detection/                 # Feature extractors
│   │   ├── temporal/                  # LSTM model
│   │   └── training/                  # Training pipeline
│   ├── doc/                           # Documentation
│   │   ├── ROBOFLOW_IMPORT.md         # Import annotated data
│   │   ├── TRAINING.md                # Training guide
│   │   ├── ARCHITECTURE.md            # Model architecture
│   │   └── DATA_COLLECTION.md         # Data collection guide
│   ├── configs/                       # Model hyperparameters
│   ├── models/                        # Trained weights
│   ├── data/                          # Frames, annotations, datasets
│   ├── run_pipeline.py                # Full training pipeline
│   ├── train_yolo_custom.py           # Custom YOLO training
│   └── import_roboflow.py             # Roboflow import script
│
├── .github/workflows/                 # CI/CD pipelines
└── README.md                          # This file
```

---

## Quick Start

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.8+ |
| Node.js | 18+ |
| PostgreSQL | Any recent version |
| Docker | Optional (for go2rtc) |

### 1. Set Up Database

```bash
# Create database
psql -U postgres -c "CREATE DATABASE milking_monitor;"

# Push schema
cd Monitoring_App/milking-monitor
npx drizzle-kit push
```

### 2. Set Up Inference Service

```bash
cd Monitoring_App/milking-monitor/apps/inference-service
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Configure .env
RTSP_STREAM_URL=rtsp://admin:password@camera-ip:554/Streaming/Channels/101
WEB_APP_INGEST_URL=http://localhost:3000/api/events/ingest
WEB_APP_INGEST_TOKEN=inference-secret-token
USE_HYBRID_MODEL=true

# Start
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

### 3. Set Up Web App

```bash
cd Monitoring_App/milking-monitor/apps/web
npm install

# Configure .env.local
DATABASE_URL=postgres://Ayman:LUZAmaxxp001@localhost:5432/milking_monitor
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret
INFERENCE_SERVICE_URL=http://localhost:8001
INFERENCE_SERVICE_TOKEN=inference-secret-token

# Start
npm run dev
```

### 4. Set Up Camera Streaming (Optional)

```bash
cd Monitoring_App/milking-monitor/apps/go2rtc
docker-compose up -d
```

---

## AI Model Architecture

The system uses a **multimodal LSTM** model for real-time milking task detection:

```
Frame (1248x576)
    |
    +------------------------+
    v                        v
+-------------+      +-------------+
| YOLOv8-Pose |      | YOLOv8n     |
| (keypoints) |      | (objects)   |
+------+------+      +------+------+
       |                    |
       v                    v
   512 dims             128 dims
       |                    |
       +----------+---------+
                  v
           640 dims/frame
                  |
                  v
         +-----------------+
         | LSTM Model      |
         | (30 frames)     |
         +--------+--------+
                  |
                  v
         +-----------------+
         | 6 Task Classes  |
         +-----------------+
```

### Model Specs

| Component | Details |
|-----------|---------|
| **Pose Features** | 512 dims — person detection, arm pose, row position, keypoints, motion, action |
| **Object Features** | 128 dims — class counts, confidence, spatial grid, temporal stats |
| **LSTM** | 2.3M params, hidden=256, 2 layers, bidirectional, dropout=0.3 |
| **Attention** | Self-attention pooling over time steps |
| **Input** | 30 frames @ 5 FPS = 6 seconds |
| **Output** | 6 task probabilities |
| **Val Accuracy** | **73.53%** |

### Detected Tasks

| Task | Name | Visual Signal |
|------|------|---------------|
| TASK-01 | Pre-cleaning | Person holds pipe, arms raised |
| TASK-02 | Stripping | Person hand on udder |
| TASK-03 | Machine attachment | Person crouching at cow |
| TASK-04 | Milking | Cups on udder, person walking |
| TASK-05 | Detachment | Cups dangling in holder |
| TASK-06 | Post-dip | Person at dip station |

For detailed architecture docs, see [`hybrid-model/doc/`](hybrid-model/doc/).

---

## API Endpoints

### FastAPI — Port `8001`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/active-sessions` | List running inference sessions |
| `POST` | `/session-window` | Start inference for a session |
| `POST` | `/session-window/{session_id}/stop` | Stop inference |

### Next.js — Port `3000`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/sessions` | List all sessions |
| `POST` | `/api/sessions` | Create a new session |
| `GET` | `/api/sessions/active` | Get active session |
| `POST` | `/api/sessions/{id}/status` | Update session status |
| `POST` | `/api/events/ingest` | Event ingestion (task + cow_process) |
| `GET` | `/api/ws?session_id={id}` | Server-Sent Events for real-time updates |

---

## Business Logic

### Task Sequence

| # | Task | Detection Signal |
|---|---|---|
| 1 | **TASK-01** — Pre-cleaning | Person + arm raised (pipe/sprayer) |
| 2 | **TASK-02** — Stripping | Person + stripping cup |
| 3 | **TASK-03** — Machine attachment | Person crouching at cow |
| 4 | **TASK-04** — Milking | Cups on udder, person walking |
| 5 | **TASK-05** — Detachment | Cups dangling in holder |
| 6 | **TASK-06** — Post-dip | Person at dip station |

### State Machine Rules

- Tasks progress sequentially when required signals are detected
- Temporal smoothing (3/5 consecutive predictions) prevents flickering
- Minimum 5s per task, 3s between switches
- Task completion at 10% of session frames
- Auto-stop at estimated end time (deadline watchdog)
- Cow process tracking (TASK-03 = started, TASK-05 = completed)

---

## Real-Time Event Flow

```
Camera/Video -> RTSP Reader -> Multimodal Extractor -> LSTM -> Task State Machine
                                                                    |
                                                                    v
                                                            Event Publisher
                                                                    |
                                                                    v
                                                            Next.js API
                                                                    |
                                                                    v
                                                            SSE -> Dashboard
```

1. RTSP reader captures frames from camera or fallback video
2. Multimodal extractor runs YOLOv8-Pose + YOLOv8n (~0.24s/frame)
3. 30-frame buffer sent to LSTM for inference
4. Task state machine applies temporal smoothing and detects switches
5. Events published to web app via HTTP
6. Web app stores events and broadcasts via SSE
7. Dashboard updates in real time

---

## Dashboard Features

- **Live Session Streaming** — real-time video and task data via SSE
- **Compliance Checklist** — interactive task status with override support
- **Session Management** — create, view, and manage milking sessions
- **Report Generation** — PDF and DOCX reports with compliance metrics
- **Cow Process Tracking** — per-cow milking progress
- **Employee Performance** — operator compliance scores

---

## Security & Authentication

### NextAuth Configuration

- **Credentials Provider:** username/password authentication
- **Email Provider:** Resend for magic links
- **Session Management:** secure session handling
- **CSRF Protection:** built-in CSRF protection

### Authorization

- **RBAC Support:** role-based access control for organizations
- **Session Validation:** supervisor and employee validation
- **Override Permissions:** authorized staff can override task statuses

---

## Development & Testing

### CI/CD Pipeline

GitHub Actions runs three jobs on every push:

| Job | Checks |
|-----|--------|
| **web-checks** | TypeScript compile, ESLint, unit tests (Vitest) |
| **inference-checks** | Python lint (ruff), type check, unit tests (pytest) |
| **integration-checks** | Cross-service validation, schema checks |

### Running Tests

```bash
# Web app
cd Monitoring_App/milking-monitor/apps/web
npm run test

# Inference service
cd Monitoring_App/milking-monitor/apps/inference-service
python -m pytest tests/
ruff check src/
```

---

## Deployment

### Docker (go2rtc)

```yaml
version: '3.8'
services:
  go2rtc:
    image: alexxit/go2rtc
    ports:
      - "1984:1984"
      - "8554:8554"
      - "8555:8555"
    volumes:
      - ./go2rtc.yaml:/config/go2rtc.yaml
      - ../../hybrid-model/data/raw/full_clip.mov:/config/full_clip.mov
```

### Environment Variables

| Service | Key Variables |
|---------|--------------|
| **Inference** | `RTSP_STREAM_URL`, `WEB_APP_INGEST_TOKEN`, `USE_HYBRID_MODEL` |
| **Web** | `DATABASE_URL`, `NEXTAUTH_SECRET`, `INFERENCE_SERVICE_TOKEN` |
| **Camera** | `go2rtc.yaml` with stream configuration |

---

## Troubleshooting

| Issue | What to Check |
|---|---|
| Database connection | Verify `DATABASE_URL` and PostgreSQL availability |
| RTSP stream | Camera is cloud-relayed (HikConnect) — requires port forwarding |
| Model not loading | Check `models/checkpoints/best_model.pt` exists |
| Task not detected | Lower `HYBRID_THRESHOLD` in `.env` (default 0.15) |
| Session not ending | Check deadline watchdog (10s interval) |
| Event not received | Verify `INFERENCE_SERVICE_TOKEN` matches |

### Logs

```bash
# Inference service
uvicorn src.main:app --reload  # logs to stdout

# Check training logs
cat hybrid-model/train_error.log
```

---

## Documentation

| Document | Location | Description |
|----------|----------|-------------|
| Inference Service | [`inference-service/README.md`](Monitoring_App/milking-monitor/apps/inference-service/README.md) | Backend API and setup |
| Hybrid Model | [`hybrid-model/README.md`](hybrid-model/README.md) | AI model architecture |
| Roboflow Import | [`hybrid-model/doc/ROBOFLOW_IMPORT.md`](hybrid-model/doc/ROBOFLOW_IMPORT.md) | Import annotated data |
| Training Guide | [`hybrid-model/doc/TRAINING.md`](hybrid-model/doc/TRAINING.md) | How to train models |
| Architecture | [`hybrid-model/doc/ARCHITECTURE.md`](hybrid-model/doc/ARCHITECTURE.md) | Model architecture details |
| Data Collection | [`hybrid-model/doc/DATA_COLLECTION.md`](hybrid-model/doc/DATA_COLLECTION.md) | Collect training data |

---

## License

**Commercial — All rights reserved by Ayman Holding**

This project contains proprietary components and intellectual property protected under applicable copyright and intellectual property laws. Unauthorized use is strictly prohibited.

---

<div align="center">

*For detailed documentation, see the `doc/` folders in each component.*

</div>
