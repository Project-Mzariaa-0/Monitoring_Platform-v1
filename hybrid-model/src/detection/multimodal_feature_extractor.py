"""
Multimodal feature extractor: Pose + Object Detection.

Runs both YOLOv8-Pose and YOLOv8n on each frame, concatenates features
into a single vector for the LSTM.

Combined feature vector (640 dims):
  0-511:   Pose features (from YOLOv8-Pose)
 512-639:  Object features (from YOLOv8n)
"""

import logging
import numpy as np
import cv2
from typing import List
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class MultimodalFrameFeatures:
    feature_vector: np.ndarray  # (640,) combined
    pose_features: np.ndarray   # (512,) pose
    object_features: np.ndarray # (128,) objects
    num_persons: int
    persons: list
    detections: dict


class MultimodalFeatureExtractor:
    def __init__(self, config):
        self.config = config
        self.feature_size = 640  # 512 (pose) + 128 (objects)

        from detection.pose_feature_extractor import PoseFeatureExtractor
        from detection.object_feature_extractor import ObjectFeatureExtractor

        self.pose_extractor = PoseFeatureExtractor(config)
        self.object_extractor = ObjectFeatureExtractor(config)

        self._frame_count = 0

        logger.info("MultimodalFeatureExtractor initialized: pose(512) + objects(128) = %d dims", self.feature_size)

    def extract_features(self, frame: np.ndarray, frame_idx: int = 0) -> MultimodalFrameFeatures:
        t0 = __import__('time').monotonic()

        # Run both detectors
        pose_result = self.pose_extractor.extract_features(frame, frame_idx)
        obj_result = self.object_extractor.extract_features(frame, frame_idx)

        t1 = __import__('time').monotonic()

        self._frame_count += 1
        if self._frame_count <= 5 or self._frame_count % 50 == 0:
            logger.info(
                "Multimodal extraction: %.2fs (pose + objects) frame=%d",
                t1 - t0, frame_idx,
            )

        # Concatenate: [pose(512), objects(128)] = (640,)
        combined = np.concatenate([
            pose_result.feature_vector,
            obj_result.feature_vector,
        ])

        return MultimodalFrameFeatures(
            feature_vector=combined,
            pose_features=pose_result.feature_vector,
            object_features=obj_result.feature_vector,
            num_persons=pose_result.num_persons,
            persons=pose_result.persons,
            detections=obj_result.detections,
        )

    def extract_sequence_features(self, frames: List[np.ndarray]) -> np.ndarray:
        self.reset()
        sequence_features = []
        for i, frame in enumerate(frames):
            frame_features = self.extract_features(frame, frame_idx=i)
            sequence_features.append(frame_features.feature_vector)
        return np.array(sequence_features)

    def reset(self) -> None:
        self.pose_extractor.reset()
        self.object_extractor.reset()
        self._frame_count = 0
