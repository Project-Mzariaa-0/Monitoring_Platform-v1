from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.runtime.session_runner import SessionRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Inference Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_runners: dict[str, SessionRunner] = {}
active_threads: dict[str, threading.Thread] = {}


class SessionWindowPayload(BaseModel):
    session_id: str
    start_time: str
    end_time: str
    cow_positions: list[int] = Field(default_factory=lambda: [1, 2])


def load_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def get_rois() -> dict:
    config_path = Path(__file__).resolve().parent / "config" / "rois.json"
    return load_json_file(config_path)


def get_thresholds() -> dict:
    config_path = Path(__file__).resolve().parent / "config" / "thresholds.json"
    return load_json_file(config_path)


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/active-sessions")
def list_active_sessions() -> dict[str, list[str]]:
    return {"sessions": list(active_runners.keys())}


@app.post("/session-window")
def receive_session_window(payload: SessionWindowPayload) -> dict[str, str]:
    logger.info("Received session window for session %s", payload.session_id)

    if payload.session_id in active_runners:
        raise HTTPException(status_code=409, detail=f"Session {payload.session_id} is already running")

    stream_url = os.getenv("RTSP_STREAM_URL")
    if not stream_url:
        raise HTTPException(status_code=400, detail="RTSP_STREAM_URL is not configured")

    ingest_url = os.getenv("WEB_APP_INGEST_URL")
    ingest_token = os.getenv("WEB_APP_INGEST_TOKEN")
    if not ingest_url or not ingest_token:
        raise HTTPException(status_code=400, detail="WEB_APP_INGEST_URL and WEB_APP_INGEST_TOKEN are required")

    weights_path = os.getenv("MODEL_WEIGHTS_PATH", "yolov8n.pt")
    rois = get_rois()
    thresholds = get_thresholds()

    runner = SessionRunner(
        session_id=payload.session_id,
        stream_url=stream_url,
        ingest_url=ingest_url,
        ingest_token=ingest_token,
        weights_path=weights_path,
        rois=rois,
        thresholds=thresholds,
    )

    thread = threading.Thread(target=runner.run, daemon=True)
    active_runners[payload.session_id] = runner
    active_threads[payload.session_id] = thread
    thread.start()

    logger.info("Started inference for session %s", payload.session_id)
    return {"status": "processing", "session_id": payload.session_id}


@app.post("/test-send")
def test_send_events(payload: SessionWindowPayload) -> dict[str, str]:
    """Send fake events to Next.js ingest to test the full pipeline."""
    ingest_url = os.getenv("WEB_APP_INGEST_URL")
    ingest_token = os.getenv("WEB_APP_INGEST_TOKEN")
    if not ingest_url or not ingest_token:
        raise HTTPException(status_code=400, detail="WEB_APP_INGEST_URL and WEB_APP_INGEST_TOKEN are required")

    import httpx

    tasks = [
        ("TASK-01", "preparing", 0.82, 1),
        ("TASK-02", "preparing", 0.78, 1),
        ("TASK-03", "attached", 0.96, 1),
        ("TASK-04", "attached", 0.91, 1),
        ("TASK-05", "detached", 0.95, 1),
        ("TASK-06", "finalizing", 0.80, 1),
    ]

    sent = 0
    for task_id, status, confidence, cow_pos in tasks:
        event = {
            "session_id": payload.session_id,
            "event_type": "task_event",
            "task_id": task_id,
            "cow_position": cow_pos,
            "status": "completed",
            "confidence_score": confidence,
            "detected_start_time": "2026-07-03T12:00:00Z",
            "detected_end_time": "2026-07-03T12:00:10Z",
            "duration_seconds": 10,
        }
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                ingest_url,
                json=event,
                headers={"Authorization": f"Bearer {ingest_token}"},
            )
            if response.status_code == 200:
                sent += 1
                logger.info("Test event %s sent OK", task_id)
            else:
                logger.error("Test event %s failed: %s %s", task_id, response.status_code, response.text)

    return {"status": "ok", "sent": sent, "session_id": payload.session_id}


@app.post("/session-window/{session_id}/stop")
def stop_session_window(session_id: str) -> dict[str, str]:
    runner = active_runners.get(session_id)
    if runner is None:
        raise HTTPException(status_code=404, detail="Session runner not found")

    runner.stop()
    active_runners.pop(session_id, None)
    active_threads.pop(session_id, None)
    logger.info("Stopped inference for session %s", session_id)
    return {"status": "stopping", "session_id": session_id}
