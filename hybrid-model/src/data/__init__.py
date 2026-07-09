"""
Data processing module.
"""

from .extract_frames import (
    extract_frames_from_video,
    create_annotations_from_labels,
    split_dataset
)

__all__ = [
    "extract_frames_from_video",
    "create_annotations_from_labels",
    "split_dataset"
]
