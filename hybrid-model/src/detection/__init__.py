"""
Detection module for YOLO-based feature extraction.
"""

from .yolo_detector import YOLOFeatureExtractor, Detection, FrameFeatures

__all__ = ["YOLOFeatureExtractor", "Detection", "FrameFeatures"]
