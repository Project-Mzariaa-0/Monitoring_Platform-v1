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


def _duration_seconds(start_time: str, end_time: str) -> int:
    try:
        t_start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        t_end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        return max(0, int((t_end - t_start).total_seconds()))
    except (ValueError, TypeError):
        return 0


def _majority_position(counts: dict[int, int]) -> int:
    if not counts:
        return 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


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
            if reader:
                logger.info("Session %s: stream health=%s", self.session_id, reader.health.snapshot())
            total_frames = reader.health.snapshot().get("frames_received", frame_count) if reader else frame_count
            logger.info("Session %s: pipeline stopped after %d frames", self.session_id, total_frames)
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

        from src.detection.yolo_detector import YoloDetector
        from src.ingestion.roi_splitter import split_frame_into_rois
        from src.state_machine.cow_process_boundary import CowProcessBoundaryDetector

        yolo = YoloDetector(self.weights_path)
        boundary_detector = CowProcessBoundaryDetector(self.thresholds)

        frame_count = 0
        COMPLETION_THRESHOLD = 0.10  # 10% of total frames (tasks happen sequentially)

        # Collect all predictions: task_id -> list of (timestamp, confidence)
        task_predictions: dict[str, list[tuple[str, float]]] = {
            "TASK-01": [], "TASK-02": [], "TASK-03": [],
            "TASK-04": [], "TASK-05": [], "TASK-06": [],
        }
        # Track frame-level predictions: what was detected on each frame
        frame_log: list[dict] = []
        # Track cow process boundaries based on hybrid task detections
        cow_process_started: dict[int, bool] = {1: False, 2: False}

        # Track which position each task was detected at (majority vote on publish)
        task_position_counts: dict[str, dict[int, int]] = {
            "TASK-01": {}, "TASK-02": {}, "TASK-03": {},
            "TASK-04": {}, "TASK-05": {}, "TASK-06": {},
        }
        # Tasks already published during the session (incremental persistence so a
        # crash/kill after the loop can no longer wipe the session's task data)
        published_tasks: set[str] = set()
        PUBLISH_FRAME_THRESHOLD = 25  # ~5s of detections at 5 FPS

        try:
            for frame_index, frame in reader.read_frames():
                if self.stop_event.is_set():
                    logger.info("Session %s: stop signal received after %d frames", self.session_id, frame_count)
                    break

                if deadline and datetime.now(timezone.utc) >= deadline:
                    logger.info("Session %s: reached end_time after %d frames, auto-stopping", self.session_id, frame_count)
                    break

                loop_start = time.monotonic()

                cow_position = self._detect_cow_position(yolo, frame, self.rois)

                roi_frames = split_frame_into_rois(frame, self.rois)
                for pos, roi_frame in roi_frames.items():
                    detections = yolo.detect(roi_frame)
                    for event in boundary_detector.update(self.session_id, pos, detections):
                        publisher.publish(build_cow_process_event(event))

                detection = manager.detect(frame)
                now_iso = datetime.now(timezone.utc).isoformat()

                if detection:
                    # Record the prediction
                    task_predictions[detection.task_id].append((now_iso, detection.confidence))
                    position_counts = task_position_counts[detection.task_id]
                    position_counts[cow_position] = position_counts.get(cow_position, 0) + 1
                    frame_log.append({
                        "frame": frame_count,
                        "task_id": detection.task_id,
                        "task_name": detection.task_name,
                        "confidence": detection.confidence,
                        "timestamp": now_iso,
                    })
                    if frame_count % 30 == 0:
                        logger.info("Session %s: frame %d detected %s (%.2f)", self.session_id, frame_count, detection.task_id, detection.confidence)

                    # Publish the task event as soon as it has enough evidence so data
                    # is persisted even if the session is killed before final analysis
                    if detection.task_id not in published_tasks and len(task_predictions[detection.task_id]) >= PUBLISH_FRAME_THRESHOLD:
                        published_tasks.add(detection.task_id)
                        preds = task_predictions[detection.task_id]
                        avg_confidence = sum(c for _, c in preds) / len(preds)
                        start_time = preds[0][0]
                        end_time = preds[-1][0]
                        duration = _duration_seconds(start_time, end_time)
                        event = {
                            "session_id": self.session_id,
                            "task_id": detection.task_id,
                            "cow_position": _majority_position(position_counts),
                            "status": "completed",
                            "completion_percentage": min(100.0, PUBLISH_FRAME_THRESHOLD * 100.0 / max(1, frame_count + 1)),
                            "confidence_score": avg_confidence,
                            "detected_start_time": start_time,
                            "detected_end_time": end_time,
                            "duration_seconds": duration,
                        }
                        publisher.publish(build_task_event(event))
                        logger.info(
                            "Session %s: %s published early (completed, %d detections) pos=%d",
                            self.session_id, detection.task_id, len(preds), event["cow_position"],
                        )

                    # Drive cow process boundaries from task detections
                    if detection.task_id == "TASK-03" and not cow_process_started.get(cow_position, False):
                        cow_process_started[cow_position] = True
                        cow_event = {
                            "session_id": self.session_id,
                            "cow_position": cow_position,
                            "event_type": "started",
                            "detected_time": now_iso,
                        }
                        try:
                            publisher.publish(build_cow_process_event(cow_event))
                        except Exception:
                            pass
                    elif detection.task_id == "TASK-05" and cow_process_started.get(cow_position, False):
                        cow_process_started[cow_position] = False
                        cow_event = {
                            "session_id": self.session_id,
                            "cow_position": cow_position,
                            "event_type": "completed",
                            "detected_time": now_iso,
                        }
                        try:
                            publisher.publish(build_cow_process_event(cow_event))
                        except Exception:
                            pass

                frame_count += 1
                if frame_count % 100 == 0:
                    logger.info("Session %s: processed %d frames", self.session_id, frame_count)

                elapsed = time.monotonic() - loop_start
                remaining = FRAME_INTERVAL - elapsed
                if remaining > 0:
                    time.sleep(remaining)
                else:
                    time.sleep(MIN_YIELD_SLEEP)
        finally:
            manager.release(self.session_id)

        # === SESSION END: Analyze all collected data ===
        logger.info("Session %s: session ended, analyzing %d frames of data", self.session_id, frame_count)

        if frame_count == 0:
            logger.warning("Session %s: no frames processed", self.session_id)
            return

        completed_tasks: set[str] = set()
        missed_tasks: set[str] = set()

        for task_id, predictions in task_predictions.items():
            position = _majority_position(task_position_counts.get(task_id) or {})

            if task_id in published_tasks:
                # Already persisted incrementally during the session — nothing to send
                detected_frames = len(predictions)
                ratio = detected_frames / frame_count
                avg_confidence = sum(c for _, c in predictions) / len(predictions) if predictions else 0.0
                logger.info(
                    "Session %s: %s already published (%d/%d frames, %.1f%%, avg_conf=%.2f, pos=%d)",
                    self.session_id, task_id, detected_frames, frame_count, ratio * 100, avg_confidence, position,
                )
                completed_tasks.add(task_id)
                continue

            if not predictions:
                # Task never detected at all — publish missed event so it shows in web app
                missed_tasks.add(task_id)
                now = datetime.now(timezone.utc).isoformat()
                event = {
                    "session_id": self.session_id,
                    "task_id": task_id,
                    "cow_position": position,
                    "status": "missed",
                    "completion_percentage": 0.0,
                    "confidence_score": 0.0,
                    "detected_start_time": now,
                    "detected_end_time": now,
                    "duration_seconds": 0,
                }
                publisher.publish(build_task_event(event))
                logger.info("Session %s: %s NEVER DETECTED -> missed (pos=%d)", self.session_id, task_id, position)
                continue

            # Calculate detection ratio: frames where task was detected / total frames
            detected_frames = len(predictions)
            ratio = detected_frames / frame_count

            # Calculate average confidence
            avg_confidence = sum(c for _, c in predictions) / len(predictions)

            logger.info(
                "Session %s: %s detected on %d/%d frames (%.1f%%) avg_conf=%.2f",
                self.session_id, task_id, detected_frames, frame_count, ratio * 100, avg_confidence,
            )

            if ratio >= COMPLETION_THRESHOLD:
                # Task passed threshold -> mark as completed
                completed_tasks.add(task_id)
                start_time = predictions[0][0]
                end_time = predictions[-1][0]
                duration = _duration_seconds(start_time, end_time)

                event = {
                    "session_id": self.session_id,
                    "task_id": task_id,
                    "cow_position": position,
                    "status": "completed",
                    "completion_percentage": min(100.0, max(0.0, ratio * 100.0)),
                    "confidence_score": avg_confidence,
                    "detected_start_time": start_time,
                    "detected_end_time": end_time,
                    "duration_seconds": duration,
                }
                publisher.publish(build_task_event(event))
                logger.info(
                    "Session %s: %s COMPLETED (%.1f%% >= threshold) avg_conf=%.2f dur=%ds pos=%d",
                    self.session_id, task_id, ratio * 100, avg_confidence, duration, position,
                )
            else:
                # Task below threshold -> mark as missed
                missed_tasks.add(task_id)
                now = datetime.now(timezone.utc).isoformat()
                event = {
                    "session_id": self.session_id,
                    "task_id": task_id,
                    "cow_position": position,
                    "status": "missed",
                    "completion_percentage": min(100.0, max(0.0, ratio * 100.0)),
                    "confidence_score": avg_confidence,
                    "detected_start_time": now,
                    "detected_end_time": now,
                    "duration_seconds": 0,
                }
                publisher.publish(build_task_event(event))
                logger.info(
                    "Session %s: %s MISSED (%.1f%% < threshold) pos=%d",
                    self.session_id, task_id, ratio * 100, position,
                )

        logger.info(
            "Session %s: FINAL - %d completed, %d missed out of 6 tasks",
            self.session_id, len(completed_tasks), len(missed_tasks),
        )

    def stop(self) -> None:
        self.stop_event.set()

    def _detect_cow_position(self, yolo, frame, rois: dict) -> int:
        from src.ingestion.roi_splitter import split_frame_into_rois

        roi_frames = split_frame_into_rois(frame, rois)
        person_counts = {}
        for pos, roi_frame in roi_frames.items():
            detections = yolo.detect(roi_frame)
            person_count = sum(1 for d in detections if getattr(d, "class_name", "") == "person")
            person_counts[pos] = person_count

        if person_counts.get(1, 0) > 0 and person_counts.get(2, 0) == 0:
            return 1
        if person_counts.get(2, 0) > 0 and person_counts.get(1, 0) == 0:
            return 2
        if person_counts.get(1, 0) > 0 and person_counts.get(2, 0) > 0:
            return 1 if person_counts[1] >= person_counts[2] else 2
        return 1
