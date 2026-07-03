from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field

from src.detection.yolo_detector import YoloDetector
from src.events.event_builder import build_cow_process_event, build_task_event
from src.events.publisher import EventPublisher
from src.ingestion.roi_splitter import split_frame_into_rois
from src.ingestion.rtsp_reader import RtspReader
from src.state_machine.cow_process_boundary import CowProcessBoundaryDetector
from src.state_machine.task_state_machine import TaskStateMachine

logger = logging.getLogger(__name__)


@dataclass
class SessionRunner:
    session_id: str
    stream_url: str
    ingest_url: str
    ingest_token: str
    weights_path: str
    rois: dict
    thresholds: dict
    stop_event: threading.Event = field(default_factory=threading.Event)

    def run(self) -> None:
        logger.info("Session %s: starting inference pipeline", self.session_id)
        try:
            reader = RtspReader(self.stream_url)
            detector = YoloDetector(self.weights_path)
            task_state_machine = TaskStateMachine(self.thresholds)
            boundary_detector = CowProcessBoundaryDetector(self.thresholds)
            publisher = EventPublisher(self.ingest_url, self.ingest_token)

            frame_count = 0
            for frame_index, frame in reader.read_frames():
                if self.stop_event.is_set():
                    logger.info("Session %s: stop signal received after %d frames", self.session_id, frame_count)
                    break

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

        except Exception:
            logger.exception("Session %s: inference pipeline failed", self.session_id)

    def stop(self) -> None:
        self.stop_event.set()
