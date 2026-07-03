from __future__ import annotations


def split_frame_into_rois(frame, rois: dict[str, dict[str, int]]):
    roi_frames: dict[int, object] = {}
    for roi_name, roi in rois.items():
        x = roi["x"]
        y = roi["y"]
        width = roi["width"]
        height = roi["height"]
        roi_frames[1 if roi_name.endswith("1") else 2] = frame[y : y + height, x : x + width]
    return roi_frames
