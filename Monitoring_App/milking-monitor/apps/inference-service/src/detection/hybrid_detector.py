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
        from detection.multimodal_feature_extractor import MultimodalFeatureExtractor
        from temporal.lstm_model import MilkingActionLSTM

        config = ModelConfig()
        config.lstm.input_size = 640
        config.lstm.hidden_size = 128
        config.lstm.num_layers = 1
        config.lstm.bidirectional = False
        config.lstm.num_classes = 6
        config.lstm.dropout = 0.7

        self.yolo = MultimodalFeatureExtractor(config)

        self.lstm = MilkingActionLSTM(
            input_size=640,
            hidden_size=128,
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

        # Temporal smoothing: require N consecutive predictions to agree
        self._prediction_history: deque[int] = deque(maxlen=10)
        self._confirmed_task: Optional[int] = None
        self._confirmed_task_start: float = 0.0
        self._min_task_duration: float = 5.0  # minimum seconds per task

        # Task transition constraints
        self._last_task_switch: float = 0.0
        self._min_switch_interval: float = 3.0  # minimum seconds between task switches

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

        # Temporal smoothing: track prediction history
        self._prediction_history.append(predicted_idx)
        
        # Count consecutive predictions for each task
        if len(self._prediction_history) < 5:
            return None  # need at least 5 predictions to confirm
        
        # Count occurrences of predicted_idx in recent history
        recent = list(self._prediction_history)[-5:]
        count = recent.count(predicted_idx)
        
        # Require at least 4 out of 5 recent predictions to agree
        if count < 4:
            if self.frame_count % 30 == 0:
                logger.info("Hybrid: frame %d prediction %d not consistent enough (%d/5)", self.frame_count, predicted_idx, count)
            return None
        
        now = time.time()
        
        # Check if we're switching tasks
        if self._confirmed_task is not None and predicted_idx != self._confirmed_task:
            # Check minimum switch interval
            if now - self._last_task_switch < self._min_switch_interval:
                return None  # too soon to switch
            
            # Check minimum duration for current task
            if now - self._confirmed_task_start < self._min_task_duration:
                logger.info("Hybrid: keeping task %d (too soon to switch, %.1fs < %.1fs)",
                           self._confirmed_task, now - self._confirmed_task_start, self._min_task_duration)
                return None  # keep current task
        
        # Confirm new task
        if predicted_idx != self._confirmed_task:
            self._confirmed_task = predicted_idx
            self._confirmed_task_start = now
            self._last_task_switch = now
            logger.info("Hybrid: CONFIRMED task switch to %s at frame %d", TASK_LABELS[predicted_idx], self.frame_count)
        
        detection = HybridDetection(
            task_id=TASK_LABELS[predicted_idx],
            task_name=TASK_NAMES[predicted_idx],
            confidence=confidence,
        )
        self.last_detection = detection
        return detection

    def reset(self) -> None:
        self.feature_buffer.clear()
        self.frame_count = 0
        self.last_detection = None
        self._last_feature = None
        self._prediction_history.clear()
        self._confirmed_task = None
        self._confirmed_task_start = 0.0
        self._last_task_switch = 0.0
