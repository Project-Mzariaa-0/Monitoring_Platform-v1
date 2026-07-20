from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.runtime.session_runner import SessionRunner, _parse_end_time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Inference Service")

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_runners: dict[str, SessionRunner] = {}
active_threads: dict[str, threading.Thread] = {}
_runner_lock = threading.Lock()


def _deadline_watchdog() -> None:
    """Background thread: every 30s, force-stop any runner past its deadline."""
    while True:
        time.sleep(30)
        now = datetime.now(timezone.utc)
        with _runner_lock:
            for sid, runner in list(active_runners.items()):
                deadline = _parse_end_time(runner.end_time)
                if deadline and now >= deadline:
                    logger.warning("Watchdog: session %s past deadline %s, force-stopping", sid, deadline.isoformat())
                    runner.stop()
                    _mark_session_completed(sid)
                    active_runners.pop(sid, None)
                    t = active_threads.pop(sid, None)
                    logger.info("Watchdog: session %s removed from active runners", sid)

WEB_APP_URL = os.getenv("WEB_APP_URL", "http://localhost:3000")


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


@app.get("/hybrid-status")
def hybrid_model_status() -> dict:
    use_hybrid = os.getenv("USE_HYBRID_MODEL", "false").lower() in ("true", "1", "yes")
    if not use_hybrid:
        return {"enabled": False, "ready": False, "loading": False, "active_session": None}

    from src.detection.hybrid_model_manager import get_hybrid_manager
    manager = get_hybrid_manager()
    return {
        "enabled": True,
        "ready": manager.is_ready,
        "loading": manager.is_loading,
        "load_error": manager.load_error,
        "active_session": manager.active_session_id,
    }


def _mark_session_active(session_id: str) -> None:
    """Tell the web app to mark this session as active."""
    _update_session_status(session_id, "active")


def _mark_session_completed(session_id: str) -> None:
    """Tell the web app to mark this session as completed."""
    _update_session_status(session_id, "completed")


def _update_session_status(session_id: str, status: str) -> None:
    """Update session status in the web app."""
    try:
        web_app_url = os.getenv("WEB_APP_URL", "http://localhost:3000")
        from src.events.publisher import _create_client
        client = _create_client(web_app_url, "")
        try:
            resp = client.post(
                f"{web_app_url}/api/sessions/{session_id}/status",
                json={"status": status},
            )
            if resp.status_code == 200:
                logger.info("Marked session %s as %s in web app", session_id, status)
            else:
                logger.warning("Failed to mark session %s as %s: %s %s", session_id, status, resp.status_code, resp.text)
        finally:
            client.close()
    except Exception:
        logger.exception("Failed to mark session %s as %s", session_id, status)


def _start_session_runner(session_id: str, start_time: str, end_time: str) -> None:
    with _runner_lock:
        if session_id in active_runners:
            logger.info("Session %s already running, skipping", session_id)
            return
        if len(active_runners) > 0:
            existing = list(active_runners.keys())
            logger.warning("Session %s rejected: session(s) %s already active (only one session at a time)", session_id, existing)
            return

    stream_url = os.getenv("RTSP_STREAM_URL")
    if not stream_url:
        logger.error("RTSP_STREAM_URL not configured, cannot start session %s", session_id)
        return

    fallback_video_path = os.getenv("FALLBACK_VIDEO_PATH")
    ingest_url = os.getenv("WEB_APP_INGEST_URL")
    ingest_token = os.getenv("WEB_APP_INGEST_TOKEN")
    if not ingest_url or not ingest_token:
        logger.error("WEB_APP_INGEST_URL/TOKEN not configured, cannot start session %s", session_id)
        return

    weights_path = os.getenv("MODEL_WEIGHTS_PATH", "yolov8n.pt")
    try:
        rois = get_rois()
        thresholds = get_thresholds()
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error("Configuration error for session %s: %s", session_id, e)
        return

    def _on_runner_stop(stopped_session_id: str) -> None:
        _mark_session_completed(stopped_session_id)
        with _runner_lock:
            active_runners.pop(stopped_session_id, None)
            active_threads.pop(stopped_session_id, None)
        logger.info("Session %s: removed from active runners", stopped_session_id)

    runner = SessionRunner(
        session_id=session_id,
        stream_url=stream_url,
        fallback_video_path=fallback_video_path,
        ingest_url=ingest_url,
        ingest_token=ingest_token,
        weights_path=weights_path,
        rois=rois,
        thresholds=thresholds,
        end_time=end_time,
        on_stop=_on_runner_stop,
        use_hybrid=os.getenv("USE_HYBRID_MODEL", "false").lower() in ("true", "1", "yes"),
    )

    thread = threading.Thread(target=runner.run, daemon=True)
    with _runner_lock:
        active_runners[session_id] = runner
        active_threads[session_id] = thread
    thread.start()
    logger.info("Started inference for session %s", session_id)

    _mark_session_active(session_id)


@app.on_event("startup")
def startup_tasks() -> None:
    """Pre-load hybrid model, start deadline watchdog, and discover scheduled sessions."""
    threading.Thread(target=_deadline_watchdog, daemon=True).start()
    logger.info("Deadline watchdog started (checks every 30s)")

    use_hybrid = os.getenv("USE_HYBRID_MODEL", "false").lower() in ("true", "1", "yes")
    if use_hybrid:
        from src.detection.hybrid_model_manager import get_hybrid_manager
        manager = get_hybrid_manager()
        manager.start_background_load()
        logger.info("Hybrid model background load started")

    def _discover():
        try:
            web_app_url = os.getenv("WEB_APP_URL", "http://localhost:3000")
            from src.events.publisher import _create_client

            client = _create_client(web_app_url, "")
            try:
                response = client.get(f"{web_app_url}/api/sessions/active")
                if response.status_code != 200:
                    logger.warning("Failed to discover sessions: %s %s", response.status_code, response.text)
                    return

                data = response.json()
                sessions = data.get("data", [])
                if not sessions:
                    logger.info("No scheduled/active sessions found on startup")
                    return

                logger.info("Discovered %d scheduled/active sessions on startup", len(sessions))
                for s in sessions:
                    sid = s["id"]
                    status = s.get("status", "scheduled")
                    start_time = s.get("scheduled_start_time", "")
                    end_time = s.get("estimated_end_time", "")
                    logger.info("  Session %s (status=%s, start=%s, end=%s)", sid, status, start_time, end_time)
                    _start_session_runner(sid, start_time, end_time)
            finally:
                client.close()
        except Exception:
            logger.exception("Failed to discover scheduled sessions on startup")

    threading.Thread(target=_discover, daemon=True).start()


@app.post("/session-window")
def receive_session_window(payload: SessionWindowPayload) -> dict[str, str]:
    logger.info("Received session window for session %s", payload.session_id)

    with _runner_lock:
        if payload.session_id in active_runners:
            raise HTTPException(status_code=409, detail=f"Session {payload.session_id} is already running")
        if len(active_runners) > 0:
            existing = list(active_runners.keys())
            raise HTTPException(status_code=409, detail=f"Session {payload.session_id} rejected: session(s) {existing} already active (only one session at a time)")

    stream_url = os.getenv("RTSP_STREAM_URL")
    if not stream_url:
        raise HTTPException(status_code=400, detail="RTSP_STREAM_URL is not configured")

    fallback_video_path = os.getenv("FALLBACK_VIDEO_PATH")

    ingest_url = os.getenv("WEB_APP_INGEST_URL")
    ingest_token = os.getenv("WEB_APP_INGEST_TOKEN")
    if not ingest_url or not ingest_token:
        raise HTTPException(status_code=400, detail="WEB_APP_INGEST_URL and WEB_APP_INGEST_TOKEN are required")

    weights_path = os.getenv("MODEL_WEIGHTS_PATH", "yolov8n.pt")
    try:
        rois = get_rois()
        thresholds = get_thresholds()
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Configuration error: {e}")

    def _on_runner_stop(stopped_session_id: str) -> None:
        _mark_session_completed(stopped_session_id)
        with _runner_lock:
            active_runners.pop(stopped_session_id, None)
            active_threads.pop(stopped_session_id, None)
        logger.info("Session %s: removed from active runners", stopped_session_id)

    runner = SessionRunner(
        session_id=payload.session_id,
        stream_url=stream_url,
        fallback_video_path=fallback_video_path,
        ingest_url=ingest_url,
        ingest_token=ingest_token,
        weights_path=weights_path,
        rois=rois,
        thresholds=thresholds,
        end_time=payload.end_time,
        on_stop=_on_runner_stop,
        use_hybrid=os.getenv("USE_HYBRID_MODEL", "false").lower() in ("true", "1", "yes"),
    )

    thread = threading.Thread(target=runner.run, daemon=True)
    with _runner_lock:
        active_runners[payload.session_id] = runner
        active_threads[payload.session_id] = thread
    thread.start()

    logger.info("Started inference for session %s", payload.session_id)
    return {"status": "processing", "session_id": payload.session_id}


@app.post("/test-send")
def test_send_events(payload: SessionWindowPayload) -> dict:
    """Send fake events to Next.js ingest to test the full pipeline."""
    ingest_url = os.getenv("WEB_APP_INGEST_URL")
    ingest_token = os.getenv("WEB_APP_INGEST_TOKEN")
    if not ingest_url or not ingest_token:
        return {"status": "error", "detail": f"Missing env vars. url={ingest_url!r} token={ingest_token!r}"}

    tasks = [
        ("TASK-01", "preparing", 0.82, 1),
        ("TASK-02", "preparing", 0.78, 1),
        ("TASK-03", "attached", 0.96, 1),
        ("TASK-04", "attached", 0.91, 1),
        ("TASK-05", "detached", 0.95, 1),
        ("TASK-06", "finalizing", 0.80, 1),
    ]

    sent = 0
    errors: list[str] = []
    try:
        from src.events.publisher import _create_client
        client = _create_client(ingest_url, ingest_token)
        client.headers["Authorization"] = f"Bearer {ingest_token}"
        try:
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
                try:
                    response = client.post(ingest_url, json=event)
                    if response.status_code == 200:
                        sent += 1
                        logger.info("Test event %s sent OK", task_id)
                    else:
                        msg = f"{task_id}: {response.status_code} {response.text}"
                        errors.append(msg)
                        logger.error("Test event %s failed: %s", task_id, msg)
                except Exception as e:
                    msg = f"{task_id}: {type(e).__name__}: {e}"
                    errors.append(msg)
                    logger.error("Test event %s exception: %s", task_id, msg)
        finally:
            client.close()
    except Exception as e:
        errors.append(f"Client init failed: {type(e).__name__}: {e}")

    return {"status": "ok", "sent": sent, "session_id": payload.session_id, "errors": errors}


@app.post("/session-window/{session_id}/stop")
def stop_session_window(session_id: str) -> dict[str, str]:
    runner = active_runners.get(session_id)
    if runner is None:
        raise HTTPException(status_code=404, detail="Session runner not found")

    runner.stop()
    with _runner_lock:
        active_runners.pop(session_id, None)
        active_threads.pop(session_id, None)
    logger.info("Stopped inference for session %s", session_id)
    return {"status": "stopping", "session_id": session_id}
