<div align="center">

# 🐄 Milking Monitor

**Real-time compliance monitoring platform for dairy farming operations**

Computer vision from RTSP camera streams + a Next.js web interface for continuous monitoring and compliance tracking.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-18+-339933?style=flat-square&logo=node.js&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-inference-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-frontend-000000?style=flat-square&logo=next.js&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-database-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/license-Commercial-red?style=flat-square)

</div>

---

## 📋 Table of Contents

- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [API Endpoints](#-api-endpoints)
- [Business Logic](#-business-logic)
- [Configuration](#-configuration)
- [Real-Time Event Flow](#-real-time-event-flow)
- [Dashboard Features](#-dashboard-features)
- [Security & Authentication](#-security--authentication)
- [Development & Testing](#-development--testing)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [Contact](#-contact)
- [License](#-license)

---

## 📁 Project Structure

```
Milking Monitor
├── apps/
│   ├── inference-service/          # Python FastAPI backend
│   │   ├── src/
│   │   │   ├── main.py             # FastAPI application
│   │   │   ├── events/             # Event handling
│   │   │   ├── runtime/            # Session management
│   │   │   ├── ingestion/          # Video stream processing
│   │   │   ├── detection/          # YOLO detection
│   │   │   └── state_machine/      # Business logic
│   │   ├── requirements.txt        # Python dependencies
│   │   └── README.md               # Backend documentation
│   │
│   └── web/                        # Next.js frontend
│       ├── app/                    # Next.js application
│       ├── components/             # React components
│       ├── lib/                    # Application libraries
│       ├── public/                 # Static assets
│       └── README.md               # Frontend documentation
│
├── .env.example                    # Environment variables template
├── README.md                       # Main project README
└── docker-compose.yml               # Docker deployment
```

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.8+ |
| Node.js | 18+ |
| PostgreSQL | Any recent version |
| Docker | Optional |

### 1. Set Up Environment

Copy the example environment file:

```bash
cp .env.example .env
```

**Database connection** — `.env`

```bash
DATABASE_URL=postgres://username:password@localhost:5432/milking_monitor
```

**Inference service** — `.env`

```bash
RTSP_STREAM_URL=rtsp://your-camera-stream
WEB_APP_INGEST_URL=http://localhost:3000/api/events/ingest
WEB_APP_INGEST_TOKEN=your-secure-token
MODEL_WEIGHTS_PATH=./yolov8n.pt
```

**Next.js** — `.env.local`

```bash
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-auth-secret
INFERENCE_SERVICE_URL=http://localhost:8001
INFERENCE_SERVICE_TOKEN=your-token
```

### 2. Install Dependencies

**Backend**

```bash
cd apps/inference-service
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Frontend**

```bash
cd apps/web
npm install
```

### 3. Run Services

**Start FastAPI (inference service)**

```bash
cd apps/inference-service
source .venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

**Start Next.js**

```bash
cd apps/web
npm run dev
```

---

## 🔌 API Endpoints

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
| `GET` | `/api/events/ingest` | Event ingestion |
| `GET` | `/api/ws?session_id={id}` | Server-Sent Events for real-time updates |

---

## 🧠 Business Logic

### Task Sequence

| # | Task | Detection Signal |
|---|---|---|
| 1 | **TASK-01** — Pre-cleaning | Person + spray bottle detection |
| 2 | **TASK-02** — Stripping | Person + stripping cup detection |
| 3 | **TASK-03** — Machine attachment | Teat cups attached |
| 4 | **TASK-04** — Milking | Teat cups attached |
| 5 | **TASK-05** — Detachment | Teat cups detached |
| 6 | **TASK-06** — Post-dip | Person + dip applicator detection |

### State Machine Rules

- Tasks progress sequentially when required signals are detected
- "Teat cups attached" states are detected for process verification
- Compliance scores are calculated from task completion rates
- `missed` events trigger compliance alerts

---

## ⚙️ Configuration

### AI Model

- **Model:** YOLOv8 with custom weights (`yolov8n.pt`)
- **ROI Definition:** Two cow positions (1 & 2)
- **Threshold Values:** Task-specific confidence thresholds
- **Detection Classes:** `person`, `spray_bottle`, `stripping_cup`, etc.

### Database Schema

| Table | Purpose |
|---|---|
| Sessions | Session metadata and status |
| Cow Processes | Cow process tracking |
| Task Events | Detailed task completion events |
| Reports | Generated compliance reports |
| Employees | Staff information |
| Audit Log | Override activity tracking |

---

## ⚡ Real-Time Event Flow

```mermaid
sequenceDiagram
    participant F as FastAPI (Inference)
    participant N as Next.js
    participant D as Dashboard (SSE)

    F->>F: Detect task completion
    F->>N: POST formatted event
    N->>N: Store event in database
    N->>D: Broadcast event via SSE
    D->>D: Update task completion in real time
```

1. FastAPI detects task completion → formats event
2. Next.js receives event → stores in database
3. Next.js broadcasts event → connected clients via SSE
4. Dashboard updates in real time → task completion tracked

### Dashboard Features

- 📹 **Live Session Streaming** — real-time video and task data
- ✅ **Compliance Checklist** — interactive task status with overrides
- 🗂️ **Session Management** — create, view, and manage sessions
- 📄 **Report Generation** — PDF and DOCX reports with compliance metrics

---

## 🔐 Security & Authentication

### NextAuth Configuration

- **Credentials Provider:** username/password authentication
- **Session Management:** secure session handling
- **CSRF Protection:** built-in CSRF protection
- **Rate Limiting:** API rate limiting implemented

### Authorization

- **RBAC Support:** role-based access control for organizations
- **Session Validation:** supervisor and employee validation
- **Override Permissions:** authorized staff can override task statuses

---

## 🧪 Development & Testing

### Testing

- **Unit Tests** — FastAPI endpoint testing
- **Integration Tests** — full workflow testing
- **E2E Tests** — complete user journey testing
- **Mock Testing** — simulated event testing

### Code Quality

- **Linting** — TypeScript and Python linting
- **Type Checking** — full TypeScript compilation
- **Code Coverage** — test coverage monitoring

---

## 🐳 Deployment

### Docker Configuration

```yaml
version: '3.8'
services:
  inference-service:
    build: ./apps/inference-service
    ports:
      - "8001:8001"
    environment:
      - RTSP_STREAM_URL=rtsp://your-camera-stream
      - WEB_APP_INGEST_URL=http://host.docker.internal:3000/api/events/ingest
    volumes:
      - ./apps/inference-service/.venv:/app/.venv

  web:
    build: ./apps/web
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_INFERENCE_URL=http://localhost:8001
    depends_on:
      - inference-service
```

### Environment-Specific Configuration

| Environment | Purpose |
|---|---|
| **Development** | Local development with hot reload |
| **Staging** | Pre-production testing |
| **Production** | Optimized for production deployment |

---

## 🛠️ Troubleshooting

| Issue | What to Check |
|---|---|
| Database connection | Verify `DATABASE_URL` and PostgreSQL availability |
| RTSP stream | Check camera connectivity and RTSP credentials |
| YOLO model | Ensure the weights file is accessible |
| Event ingestion | Verify `INFERENCE_SERVICE_TOKEN` and network connectivity |
| CORS issues | FastAPI CORS middleware handles all origins |

### Logging

```bash
# Inference service logs
cd apps/inference-service
source .venv/bin/activate
uvicorn src.main:app --reload

# Database queries
# Check application.log for detailed event processing
```

---

## 🗺️ Roadmap

- [ ] 📱 **Mobile App** — Android/iOS companion app
- [ ] 🚪 **API Gateway** — single entry point for all services
- [ ] 📊 **Monitoring** — Prometheus/Grafana integration
- [ ] 🤖 **Machine Learning** — advanced anomaly detection
- [ ] 🏢 **Multi-tenant** — support for multiple farm operations

---

## 📬 Contact

For questions, issues, or support:

- Check the [issues tracker](#) for known issues
- Review the documentation for troubleshooting
- Submit issues with detailed error messages and steps to reproduce

---

## 📄 License

**Commercial — All rights reserved by Ayman Holding**

This project contains proprietary components and intellectual property protected under applicable copyright and intellectual property laws. Unauthorized use is strictly prohibited.

---

<div align="center">

*This documentation provides complete guidance for setting up, running, and maintaining the Milking Monitor system. For more detailed technical information, refer to specific component documentation.*

</div>
