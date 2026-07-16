from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.events.event_builder import build_cow_process_event, build_task_event
from src.events.publisher import EventPublisher
from src.ingestion.roi_splitter import split_frame_into_rois
from src.ingestion.rtsp_reader import RtspReader
from src.state_machine.cow_process_boundary import CowProcessBoundaryDetector
from src.state_machine.task_state_machine import TaskStateMachine

logger = logging.getLogger(__name__)

TARGET_FPS = 5
FRAME_INTERVAL = 1.0 / TARGET_FPS
MIN_YIELD_SLEEP = 0.05


def _parse_end_time(end_time: str | None) -> datetime | None:
    if not end_time:
        return None
    try:
        cleaned = end_time.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        logger.warning("Could not parse end_time: %s", end_time)
        return None


@dataclass
class SessionRunner:
    session_id: str
    stream_url: str
    ingest_url: str
    ingest_token: str
    weights_path: str
    rois: dict
    thresholds: dict
    fallback_video_path: str | None = None
    end_time: str | None = None
    on_stop: callable | None = None
    use_hybrid: bool = False
    stop_event: threading.Event = field(default_factory=threading.Event)

    def run(self) -> None:
        mode = "hybrid" if self.use_hybrid else "yolo"
        logger.info("Session %s: starting inference pipeline (mode=%s, end_time=%s)", self.session_id, mode, self.end_time)
        frame_count = 0
        reader = None
        publisher = None
        deadline = _parse_end_time(self.end_time)
        try:
            reader = RtspReader(self.stream_url, self.fallback_video_path)
            publisher = EventPublisher(self.ingest_url, self.ingest_token)

            if self.use_hybrid:
                self._run_hybrid(reader, publisher, deadline)
            else:
                self._run_yolo(reader, publisher, deadline)

        except Exception:
            logger.exception("Session %s: inference pipeline failed", self.session_id)
        finally:
            if publisher:
                publisher.close()
            logger.info("Session %s: pipeline stopped after %d frames", self.session_id, frame_count)
            if self.on_stop:
                try:
                    self.on_stop(self.session_id)
                except Exception:
                    logger.exception("Session %s: on_stop callback failed", self.session_id)

    def _run_yolo(self, reader: RtspReader, publisher: EventPublisher, deadline: datetime | None) -> None:
        from src.detection.yolo_detector import YoloDetector

        frame_count = 0
        detector = YoloDetector(self.weights_path)
        task_state_machine = TaskStateMachine(self.thresholds)
        boundary_detector = CowProcessBoundaryDetector(self.thresholds)

        for frame_index, frame in reader.read_frames():
            if self.stop_event.is_set():
                logger.info("Session %s: stop signal received after %d frames", self.session_id, frame_count)
                break

            if deadline and datetime.now(timezone.utc) >= deadline:
                logger.info("Session %s: reached end_time after %d frames, auto-stopping", self.session_id, frame_count)
                break

            loop_start = time.monotonic()

            roi_frames = split_frame_into_rois(frame, self.rois)
            for cow_position, roi_frame in roi_frames.items():
                detections = detector.detect(roi_frame)
                for event in boundary_detector.update(self.session_id, cow_position, detections):
                    publisher.publish(build_cow_process_event(event))
                for event in task_state_machine.update(self.session_id, cow_position, detections):
                    publisher.publish(build_task_event(event))

            frame_count += 1
            if frame_count % 100 == 0:
                logger.info("Session %s: processed %d frames", self.session_id, frame_count)

            elapsed = time.monotonic() - loop_start
            remaining = FRAME_INTERVAL - elapsed
            if remaining > 0:
                time.sleep(remaining)
            else:
                time.sleep(MIN_YIELD_SLEEP)

    def _run_hybrid(self, reader: RtspReader, publisher: EventPublisher, deadline: datetime | None) -> None:
        from src.detection.hybrid_model_manager import get_hybrid_manager

        manager = get_hybrid_manager()
        if not manager.is_ready:
            logger.error("Session %s: hybrid model not ready, falling back to YOLO", self.session_id)
            self._run_yolo(reader, publisher, deadline)
            return

        if not manager.acquire(self.session_id):
            logger.error("Session %s: cannot acquire hybrid model (already in use by session %s)", self.session_id, manager.active_session_id)
            return

        frame_count = 0
        completed_tasks: set[str] = set()

        try:
            for frame_index, frame in reader.read_frames():
                if self.stop_event.is_set():
                    logger.info("Session %s: stop signal received after %d frames", self.session_id, frame_count)
                    break

                if deadline and datetime.now(timezone.utc) >= deadline:
                    logger.info("Session %s: reached end_time after %d frames, auto-stopping", self.session_id, frame_count)
                    break

                loop_start = time.monotonic()

                detection = manager.detect(frame)
                if detection and detection.task_id not in completed_tasks:
                    now = datetime.now(timezone.utc).isoformat()
                    event = {
                        "session_id": self.session_id,
                        "task_id": detection.task_id,
                        "cow_position": 1,
                        "status": "completed",
                        "confidence_score": detection.confidence,
                        "detected_start_time": now,
                        "detected_end_time": now,
                        "duration_seconds": 0,
                    }
                    publisher.publish(build_task_event(event))
                    completed_tasks.add(detection.task_id)
                    logger.info(
                        "Session %s: hybrid detected %s (%s) conf=%.2f [%d/%d tasks]",
                        self.session_id,
                        detection.task_id,
                        detection.task_name,
                        detection.confidence,
                        len(completed_tasks),
                        6,
                    )

                frame_count += 1
                if frame_count % 100 == 0:
                    logger.info("Session %s: processed %d frames (%d tasks detected)", self.session_id, frame_count, len(completed_tasks))

                elapsed = time.monotonic() - loop_start
                remaining = FRAME_INTERVAL - elapsed
                if remaining > 0:
                    time.sleep(remaining)
                else:
                    time.sleep(MIN_YIELD_SLEEP)
        finally:
            manager.release(self.session_id)

        if len(completed_tasks) < 6:
            missed = {"TASK-01", "TASK-02", "TASK-03", "TASK-04", "TASK-05", "TASK-06"} - completed_tasks
            missed_confidence = self.thresholds.get("default_unverifiable_confidence", 0.5)
            now = datetime.now(timezone.utc).isoformat()
            for task_id in sorted(missed):
                event = {
                    "session_id": self.session_id,
                    "task_id": task_id,
                    "cow_position": 1,
                    "status": "missed",
                    "confidence_score": missed_confidence,
                    "detected_start_time": now,
                    "detected_end_time": now,
                    "duration_seconds": 0,
                }
                publisher.publish(build_task_event(event))
                logger.info("Session %s: marked %s as missed (not detected)", self.session_id, task_id)

    def stop(self) -> None:
        self.stop_event.set()
