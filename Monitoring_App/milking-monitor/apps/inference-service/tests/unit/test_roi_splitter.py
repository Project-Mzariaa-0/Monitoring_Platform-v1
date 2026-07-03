from __future__ import annotations

import numpy as np
import pytest
from src.ingestion.roi_splitter import split_frame_into_rois


class TestRoiSplitter:
    def test_splits_frame_into_two_rois(self, sample_rois):
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        result = split_frame_into_rois(frame, sample_rois)
        assert len(result) == 2

    def test_roi_keys_are_positions(self, sample_rois):
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        result = split_frame_into_rois(frame, sample_rois)
        assert 1 in result
        assert 2 in result

    def test_roi_extraction_crops_correctly(self, sample_rois):
        frame = np.ones((720, 1280, 3), dtype=np.uint8) * 42
        result = split_frame_into_rois(frame, sample_rois)
        roi1 = result[1]
        assert roi1.shape == (720, 640, 3)
        assert np.all(roi1 == 42)

    def test_different_roi_values_preserved(self):
        rois = {
            "left_1": {"x": 0, "y": 0, "width": 100, "height": 100},
            "right_2": {"x": 100, "y": 0, "width": 100, "height": 100},
        }
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        frame[0:100, 0:100] = [255, 0, 0]
        frame[0:100, 100:200] = [0, 255, 0]
        result = split_frame_into_rois(frame, rois)
        assert np.all(result[1][:, :, 0] == 255)
        assert np.all(result[2][:, :, 1] == 255)
