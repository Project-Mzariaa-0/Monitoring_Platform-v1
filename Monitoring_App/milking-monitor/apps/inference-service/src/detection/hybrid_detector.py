from __future__ import annotations

import logging
import sys
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np
import torch

logger = logging.getLogger(__name__)

HYBRID_MODEL_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent / "hybrid-model"
if str(HYBRID_MODEL_DIR / "src") not in sys.path:
    sys.path.insert(0, str(HYBRID_MODEL_DIR / "src"))

TASK_LABELS = ["TASK-01", "TASK-02", "TASK-03", "TASK-04", "TASK-05", "TASK-06"]
TASK_NAMES = ["Pre-cleaning", "Stripping", "Machine attachment", "Milking", "Detachment", "Post-dip"]


@dataclass
class HybridDetection:
    task_id: str
    task_name: str
    confidence: float


class HybridDetector:
    def __init__(
        self,
        weights_path: str | None = None,
        sequence_length: int = 30,
        threshold: float = 0.4,
        yolo_skip: int = 5,
        device: str | None = None,
    ):
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.sequence_length = sequence_length
        self.threshold = threshold
        self.yolo_skip = yolo_skip

        if weights_path is None:
            weights_path = str(HYBRID_MODEL_DIR / "models" / "checkpoints" / "best_model.pt")

        from config import ModelConfig
        from detection.pose_feature_extractor import PoseFeatureExtractor
        from temporal.lstm_model import MilkingActionLSTM

        config = ModelConfig()
        config.lstm.input_size = 512
        config.lstm.hidden_size = 64
        config.lstm.num_layers = 1
        config.lstm.bidirectional = False
        config.lstm.num_classes = 6
        config.lstm.dropout = 0.7

        self.yolo = PoseFeatureExtractor(config)

        self.lstm = MilkingActionLSTM(
            input_size=512,
            hidden_size=64,
            num_layers=1,
            num_classes=6,
            dropout=0.7,
            bidirectional=False,
        ).to(self.device)

        self._load_weights(weights_path)

        self.feature_buffer: deque[np.ndarray] = deque(maxlen=sequence_length)
        self.frame_count = 0
        self.last_detection: Optional[HybridDetection] = None
        self._last_feature: np.ndarray | None = None

        logger.info("HybridDetector initialized: device=%s, weights=%s, seq_len=%d, yolo_skip=%d", self.device, weights_path, sequence_length, yolo_skip)

    def _load_weights(self, weights_path: str) -> None:
        path = Path(weights_path)
        if not path.exists():
            logger.warning("No hybrid model weights at %s, using random init", path)
            return
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        state_dict = checkpoint.get("model_state_dict", checkpoint)
        self.lstm.load_state_dict(state_dict)
        logger.info("Loaded hybrid model weights from %s", path)

    def detect(self, frame: np.ndarray) -> Optional[HybridDetection]:
        self.frame_count += 1

        if self.frame_count % self.yolo_skip == 1 or self._last_feature is None:
            t0 = time.monotonic()
            frame_features = self.yolo.extract_features(frame, frame_idx=self.frame_count)
            self._last_feature = frame_features.feature_vector
            if self.frame_count <= 30 or self.frame_count % 50 == 0:
                logger.info("Hybrid: YOLO feature extraction took %.2fs (frame %d)", time.monotonic() - t0, self.frame_count)

        self.feature_buffer.append(self._last_feature)

        if len(self.feature_buffer) < self.sequence_length:
            return None

        sequence = np.array(list(self.feature_buffer))
        tensor = torch.FloatTensor(sequence).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output, _ = self.lstm(tensor)
            probs = torch.softmax(output, dim=1)

        confidence, predicted_idx = torch.max(probs, dim=1)
        confidence = confidence.item()
        predicted_idx = predicted_idx.item()

        if confidence < self.threshold:
            if self.frame_count % 30 == 0:
                top3 = torch.topk(probs, 3)
                parts = [f"{TASK_LABELS[idx.item()]}={v.item():.3f}" for v, idx in zip(top3.values[0], top3.indices[0])]
                logger.info("Hybrid: frame %d below threshold (%.3f < %.3f) top3=[%s]", self.frame_count, confidence, self.threshold, ", ".join(parts))
            return None

        detection = HybridDetection(
            task_id=TASK_LABELS[predicted_idx],
            task_name=TASK_NAMES[predicted_idx],
            confidence=confidence,
        )
        self.last_detection = detection
        logger.info("Hybrid: DETECTED %s (%s) conf=%.3f at frame %d", detection.task_id, detection.task_name, confidence, self.frame_count)
        return detection

    def reset(self) -> None:
        self.feature_buffer.clear()
        self.frame_count = 0
        self.last_detection = None
        self._last_feature = None
