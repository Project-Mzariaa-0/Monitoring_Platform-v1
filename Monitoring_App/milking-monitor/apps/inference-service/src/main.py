from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import settings
from src.runtime.session_runner import SessionRunner, _parse_end_time
from src.services.diagnostics import build_service_status
from src.services.runtime_validation import validate_runtime_configuration
from src.services.session_manager import SessionManager
from src.services.session_runtime_service import SessionRuntimeService
from src.observability.logging import clear_request_id, configure_logging, set_request_id

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

configure_logging()
logger = logging.getLogger(__name__)
SERVICE_START_TIME = datetime.now(timezone.utc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _startup_tasks()
    try:
        yield
    finally:
        _shutdown_tasks()
        logger.info("Application shutdown complete")


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)


@app.middleware("http")
async def add_request_id(request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = set_request_id(request_id)
    try:
        response = await call_next(request)
    finally:
        clear_request_id(token)
    response.headers["X-Request-ID"] = request_id
    return response


ALLOWED_ORIGINS = settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_manager = SessionManager(settings)
session_runtime_service = SessionRuntimeService(settings, session_manager)


def _deadline_watchdog() -> None:
    """Background thread: every 10s, force-stop any runner past its deadline.

    Waits for the runner thread to exit (so end-of-session task events are
    flushed) before marking the session completed and unregistering it.
    """
    while True:
        time.sleep(10)
        now = datetime.now(timezone.utc)
        try:
            for sid, runner in list(session_manager.active_runners.items()):
                deadline = _parse_end_time(runner.end_time)
                if not (deadline and now >= deadline):
                    continue

                thread = session_manager.active_threads.get(sid)
                if not runner.stop_event.is_set():
                    logger.warning("Watchdog: session %s past deadline %s, force-stopping", sid, deadline.isoformat())
                    runner.stop()

                if thread is not None and thread.is_alive():
                    # Give the runner time to publish its end-of-session task events
                    thread.join(timeout=90)

                if thread is not None and thread.is_alive():
                    logger.warning("Watchdog: session %s still flushing after force-stop; will retry next cycle", sid)
                    continue

                if not session_manager.is_session_active(sid):
                    # Already finished via on_stop/stop endpoint (which marks completed);
                    # skip to avoid a duplicate status update.
                    continue

                try:
                    _mark_session_completed(sid)
                except Exception:
                    logger.exception("Watchdog: failed to mark session %s completed", sid)
                session_manager.unregister(sid)
                logger.info("Watchdog: session %s removed from active runners", sid)
        except Exception:
            logger.exception("Watchdog: error checking deadlines")

WEB_APP_URL = settings.web_app_url


class SessionWindowPayload(BaseModel):
    session_id: str
    start_time: str
    end_time: str
    cow_positions: list[int] = Field(default_factory=lambda: [1, 2])


def load_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def get_rois() -> dict:
    return load_json_file(settings.rois_file)


def get_thresholds() -> dict:
    return load_json_file(settings.thresholds_file)


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health")
def health_check_extended() -> dict:
    report = validate_runtime_configuration(settings)
    return {
        "status": "ok" if report["ready"] else "degraded",
        "ready": report["ready"],
        "errors": report["errors"],
        "service": build_service_status(settings, session_manager, started_at=SERVICE_START_TIME),
    }


@app.get("/ready")
def readiness_check() -> dict:
    report = validate_runtime_configuration(settings)
    return {
        "ready": report["ready"],
        "errors": report["errors"],
        "service": build_service_status(settings, session_manager, started_at=SERVICE_START_TIME),
    }


@app.get("/active-sessions")
def list_active_sessions() -> dict[str, list[str]]:
    return {"sessions": session_manager.list_active_sessions()}


@app.get("/hybrid-status")
def hybrid_model_status() -> dict:
    if not settings.use_hybrid_model:
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
        web_app_url = settings.web_app_url
        from src.events.publisher import _create_client
        ingest_token = settings.web_app_ingest_token or os.environ.get("INFERENCE_SERVICE_TOKEN", "") or ""
        client = _create_client(web_app_url, ingest_token)
        if ingest_token:
            client.headers["Authorization"] = f"Bearer {ingest_token}"
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


def _shutdown_tasks() -> None:
    for sid in list(session_manager.list_active_sessions()):
        try:
            runner = session_manager.active_runners.get(sid)
            if runner:
                runner.stop()
        except Exception:
            logger.exception("Shutdown: failed to stop session %s", sid)
        finally:
            session_manager.unregister(sid)
    logger.info("Shutdown complete: active sessions cleared")


def _start_session_runner(session_id: str, start_time: str, end_time: str) -> None:
    start_deadline = _parse_end_time(start_time)
    if start_deadline and datetime.now(timezone.utc) < start_deadline:
        delay = (start_deadline - datetime.now(timezone.utc)).total_seconds()
        logger.info("Session %s scheduled to start in %.1f seconds", session_id, delay)
        timer = threading.Timer(delay, _start_session_runner, args=(session_id, start_time, end_time))
        timer.daemon = True
        timer.start()
        return

    if not session_runtime_service.can_start_session(session_id):
        if session_manager.is_session_active(session_id):
            logger.info("Session %s already running, skipping", session_id)
        else:
            logger.warning("Session %s rejected: session(s) %s already active (only one session at a time)", session_id, session_manager.list_active_sessions())
        return

    validation = validate_runtime_configuration(settings)
    if not validation["ready"]:
        logger.error("Session %s could not start: %s", session_id, validation["errors"])
        return

    stream_url = settings.rtsp_stream_url
    fallback_video_path = settings.fallback_video_path
    ingest_url = settings.web_app_ingest_url
    ingest_token = settings.web_app_ingest_token
    weights_path = str(settings.model_weights_path)
    try:
        rois = get_rois()
        thresholds = get_thresholds()
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error("Configuration error for session %s: %s", session_id, e)
        return

    def _on_runner_stop(stopped_session_id: str) -> None:
        _mark_session_completed(stopped_session_id)
        session_manager.unregister(stopped_session_id)
        logger.info("Session %s: removed from active runners", stopped_session_id)

    runner = session_runtime_service.build_runner(
        session_id=session_id,
        end_time=end_time,
        stream_url=stream_url,
        fallback_video_path=fallback_video_path,
        ingest_url=ingest_url,
        ingest_token=ingest_token,
        weights_path=weights_path,
        rois=rois,
        thresholds=thresholds,
    )
    runner.on_stop = _on_runner_stop

    thread = threading.Thread(target=runner.run, daemon=True)
    session_manager.register(session_id, runner, thread)
    thread.start()
    logger.info("Started inference for session %s", session_id)

    _mark_session_active(session_id)


def _startup_tasks() -> None:
    """Pre-load hybrid model, start deadline watchdog, and discover scheduled sessions."""
    threading.Thread(target=_deadline_watchdog, daemon=True).start()
    logger.info("Deadline watchdog started (checks every 10s)")

    if settings.use_hybrid_model:
        from src.detection.hybrid_model_manager import get_hybrid_manager
        manager = get_hybrid_manager()
        manager.start_background_load()
        logger.info("Hybrid model background load started")

    def _discover():
        try:
            web_app_url = settings.web_app_url
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

    if not session_runtime_service.can_start_session(payload.session_id):
        if session_manager.is_session_active(payload.session_id):
            raise HTTPException(status_code=409, detail=f"Session {payload.session_id} is already running")
        existing = session_manager.list_active_sessions()
        raise HTTPException(status_code=409, detail=f"Session {payload.session_id} rejected: session(s) {existing} already active (only one session at a time)")

    validation = validate_runtime_configuration(settings)
    if not validation["ready"]:
        raise HTTPException(status_code=400, detail={"errors": validation["errors"]})

    start_deadline = _parse_end_time(payload.start_time)
    if start_deadline and datetime.now(timezone.utc) < start_deadline:
        delay = (start_deadline - datetime.now(timezone.utc)).total_seconds()
        logger.info("Session %s scheduled to start in %.1f seconds", payload.session_id, delay)
        timer = threading.Timer(
            delay,
            _start_session_runner,
            args=(payload.session_id, payload.start_time, payload.end_time),
        )
        timer.daemon = True
        timer.start()
        return {"status": "scheduled", "session_id": payload.session_id}

    stream_url = settings.rtsp_stream_url
    fallback_video_path = settings.fallback_video_path
    ingest_url = settings.web_app_ingest_url
    ingest_token = settings.web_app_ingest_token
    weights_path = str(settings.model_weights_path)
    try:
        rois = get_rois()
        thresholds = get_thresholds()
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Configuration error: {e}")

    def _on_runner_stop(stopped_session_id: str) -> None:
        _mark_session_completed(stopped_session_id)
        session_manager.unregister(stopped_session_id)
        logger.info("Session %s: removed from active runners", stopped_session_id)

    runner = session_runtime_service.build_runner(
        session_id=payload.session_id,
        end_time=payload.end_time,
        stream_url=stream_url,
        fallback_video_path=fallback_video_path,
        ingest_url=ingest_url,
        ingest_token=ingest_token,
        weights_path=weights_path,
        rois=rois,
        thresholds=thresholds,
    )
    runner.on_stop = _on_runner_stop

    thread = threading.Thread(target=runner.run, daemon=True)
    session_manager.register(payload.session_id, runner, thread)
    thread.start()

    logger.info("Started inference for session %s", payload.session_id)
    return {"status": "processing", "session_id": payload.session_id}


@app.post("/test-send")
def test_send_events(payload: SessionWindowPayload) -> dict:
    """Send fake events to Next.js ingest to test the full pipeline."""
    ingest_url = settings.web_app_ingest_url
    ingest_token = settings.web_app_ingest_token
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
                    "contract_version": "1.0",
                    "session_id": payload.session_id,
                    "event_type": "task_event",
                    "task_id": task_id,
                    "cow_position": cow_pos,
                    "status": "completed",
                    "confidence_score": confidence,
                    "completion_percentage": 100.0,
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
    runner = session_manager.active_runners.get(session_id)
    if runner is None:
        raise HTTPException(status_code=404, detail="Session runner not found")

    runner.stop()
    thread = session_manager.active_threads.get(session_id)
    if thread is not None and thread.is_alive():
        # Wait so end-of-session task-event publishing completes before marking done
        thread.join(timeout=60)
    # Persist final state immediately so session history is available even if shutdown is abrupt.
    _mark_session_completed(session_id)
    session_manager.unregister(session_id)
    logger.info("Stopped inference for session %s", session_id)
    return {"status": "stopping", "session_id": session_id}
