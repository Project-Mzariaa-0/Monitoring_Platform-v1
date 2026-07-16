from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class HybridModelManager:
    """Singleton that pre-loads the hybrid model once and enforces single-session usage."""

    _instance: Optional[HybridModelManager] = None
    _lock = threading.Lock()

    def __new__(cls) -> HybridModelManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._detector = None
        self._session_lock = threading.Lock()
        self._active_session_id: str | None = None
        self._loaded = False
        self._loading = False
        self._load_error: str | None = None

        logger.info("HybridModelManager created (model not yet loaded)")

    def start_background_load(self) -> None:
        """Load model in background thread so FastAPI startup isn't blocked."""
        if self._loaded or self._loading:
            return
        self._loading = True
        threading.Thread(target=self._load_model, daemon=True).start()

    def _load_model(self) -> None:
        t0 = time.monotonic()
        try:
            from src.detection.hybrid_detector import HybridDetector

            weights_path = os.getenv("HYBRID_MODEL_WEIGHTS")
            if not weights_path:
                weights_path = str(
                    Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent
                    / "hybrid-model" / "models" / "checkpoints" / "best_model.pt"
                )

            self._detector = HybridDetector(
                weights_path=weights_path,
                sequence_length=int(os.getenv("HYBRID_SEQUENCE_LENGTH", "30")),
                threshold=float(os.getenv("HYBRID_THRESHOLD", "0.15")),
                yolo_skip=int(os.getenv("HYBRID_YOLO_SKIP", "5")),
            )
            self._loaded = True
            self._loading = False
            elapsed = time.monotonic() - t0
            logger.info("Hybrid model loaded successfully in %.1fs", elapsed)
        except Exception as e:
            self._loading = False
            self._load_error = str(e)
            logger.exception("Failed to load hybrid model: %s", e)

    @property
    def is_ready(self) -> bool:
        return self._loaded and self._detector is not None

    @property
    def is_loading(self) -> bool:
        return self._loading

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def acquire(self, session_id: str) -> bool:
        """Try to acquire the model for a session. Returns False if already in use."""
        if not self.is_ready:
            logger.warning("Hybrid model not ready, cannot acquire for session %s", session_id)
            return False

        acquired = self._session_lock.acquire(blocking=False)
        if acquired:
            self._active_session_id = session_id
            self._detector.reset()
            logger.info("Hybrid model acquired for session %s", session_id)
            return True
        else:
            logger.warning("Hybrid model already in use by session %s, rejecting session %s", self._active_session_id, session_id)
            return False

    def release(self, session_id: str) -> None:
        """Release the model back to idle state."""
        if self._active_session_id == session_id:
            self._active_session_id = None
            self._detector.reset()
            self._session_lock.release()
            logger.info("Hybrid model released from session %s", session_id)
        else:
            logger.warning("Release called for session %s but active session is %s", session_id, self._active_session_id)

    def detect(self, frame: np.ndarray):
        """Run detection on a frame. Must be called between acquire/release."""
        if not self.is_ready:
            return None
        return self._detector.detect(frame)

    @property
    def active_session_id(self) -> str | None:
        return self._active_session_id


_hybrid_manager: HybridModelManager | None = None


def get_hybrid_manager() -> HybridModelManager:
    global _hybrid_manager
    if _hybrid_manager is None:
        _hybrid_manager = HybridModelManager()
    return _hybrid_manager
