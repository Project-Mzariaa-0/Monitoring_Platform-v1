"""
Object detection feature extractor using YOLOv8n.

Runs YOLOv8n on frames to detect objects and extract a fixed-size feature vector.
Even when detection is poor, the ABSENCE of detections is itself a feature.

Feature vector (128 dims):
   0-6:    Per-class detection count (7 tracked classes)
   7-13:   Per-class max confidence
  14-20:   Per-class binary (detected or not)
  21-27:   Per-class avg bbox center x
  28-34:   Per-class avg bbox center y
  35-41:   Per-class avg bbox width
  42-48:   Per-class avg bbox height
  49-58:   Aggregate stats (total, person, non-person, ratio, sizes)
  59-70:   Spatial grid distribution
  71-85:   Temporal running stats
  86-127:  Object-person proximity and detection quality
"""

import logging
import numpy as np
from typing import Dict, Tuple
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class ObjectFrameFeatures:
    feature_vector: np.ndarray
    detections: Dict[int, list]


class ObjectFeatureExtractor:
    def __init__(self, config):
        from ultralytics import YOLO

        self.config = config
        self.model = YOLO("yolov8n.pt")

        self.feature_size = 128

        self._count_history: deque = deque(maxlen=30)
        self._conf_history: deque = deque(maxlen=30)
        self._total_obj_history: deque = deque(maxlen=30)

        self._class_names = self.model.names
        self._num_classes = len(self._class_names)

        logger.info("ObjectFeatureExtractor: loaded yolov8n.pt (%d classes)", self._num_classes)

    def extract_features(self, frame: np.ndarray, frame_idx: int = 0) -> ObjectFrameFeatures:
        h_orig, w_orig = frame.shape[:2]
        results = self.model(
            frame,
            conf=self.config.yolo.confidence,
            imgsz=self.config.yolo.input_size,
            verbose=False,
        )

        objects_by_class: Dict[int, list] = {}

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls.item())
                confidence = float(box.conf.item())
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                bbox = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                center = (int((x1 + x2) / 2), int((y1 + y2) / 2))

                if cls_id not in objects_by_class:
                    objects_by_class[cls_id] = []
                objects_by_class[cls_id].append({
                    "bbox": bbox,
                    "center": center,
                    "confidence": confidence,
                })

        feature_vector = self._create_feature_vector(objects_by_class, (h_orig, w_orig))

        return ObjectFrameFeatures(
            feature_vector=feature_vector,
            detections=objects_by_class,
        )

    def _create_feature_vector(
        self,
        objects_by_class: Dict[int, list],
        frame_shape: Tuple[int, int],
    ) -> np.ndarray:
        h, w = frame_shape
        features = np.zeros(self.feature_size)

        total_objects = sum(len(v) for v in objects_by_class.values())
        all_confs = [obj["confidence"] for objs in objects_by_class.values() for obj in objs]
        avg_conf = np.mean(all_confs) if all_confs else 0.0

        tracked_classes = [0, 39, 41, 42, 43, 44, 77]

        for i, cls_id in enumerate(tracked_classes):
            objs = objects_by_class.get(cls_id, [])
            count = len(objs)

            features[i] = min(count / 3.0, 1.0)
            features[7 + i] = max((o["confidence"] for o in objs), default=0.0)
            features[14 + i] = 1.0 if count > 0 else 0.0

            if objs:
                features[21 + i] = np.mean([o["center"][0] / w for o in objs])
                features[28 + i] = np.mean([o["center"][1] / h for o in objs])
                features[35 + i] = np.mean([o["bbox"][2] / w for o in objs])
                features[42 + i] = np.mean([o["bbox"][3] / h for o in objs])

        person_objs = objects_by_class.get(0, [])
        non_person = total_objects - len(person_objs)

        features[49] = min(total_objects / 10.0, 1.0)
        features[50] = avg_conf
        features[51] = min(len(person_objs) / 3.0, 1.0)
        features[52] = len(person_objs)
        features[53] = min(non_person / 5.0, 1.0)
        features[54] = non_person

        if len(person_objs) > 0:
            features[55] = min(non_person / len(person_objs), 3.0) / 3.0
        else:
            features[55] = 0.0

        all_sizes = []
        for objs in objects_by_class.values():
            for o in objs:
                all_sizes.append((o["bbox"][2] * o["bbox"][3]) / (w * h))
        features[56] = max(all_sizes) if all_sizes else 0.0
        features[57] = np.mean(all_sizes) if all_sizes else 0.0
        features[58] = min(len(objects_by_class) / 5.0, 1.0)

        all_centers = []
        for cls_id, objs in objects_by_class.items():
            if cls_id == 0:
                continue
            for o in objs:
                all_centers.append((o["center"][0] / w, o["center"][1] / h))

        grid_cols, grid_rows = 3, 3
        for gi in range(9):
            gr, gc = divmod(gi, grid_cols)
            x_start = gc / grid_cols
            x_end = (gc + 1) / grid_cols
            y_start = gr / grid_rows
            y_end = (gr + 1) / grid_rows
            count_in_cell = sum(
                1 for cx, cy in all_centers
                if x_start <= cx < x_end and y_start <= cy < y_end
            )
            features[59 + gi] = min(count_in_cell / 3.0, 1.0)

        if all_centers:
            xs = [c[0] for c in all_centers]
            ys = [c[1] for c in all_centers]
            features[68] = np.std(xs)
            features[69] = np.std(ys)
            features[70] = len(set(
                (int(cx * grid_cols), int(cy * grid_rows))
                for cx, cy in all_centers
            )) / 9.0

        self._count_history.append(total_objects)
        self._conf_history.append(avg_conf)
        self._total_obj_history.append(non_person)

        if len(self._count_history) >= 3:
            counts = list(self._count_history)
            features[71] = np.mean(counts)
            features[72] = np.std(counts)
            features[73] = max(counts) - min(counts)
            features[74] = counts[-1] - counts[0]

        if len(self._conf_history) >= 3:
            confs = list(self._conf_history)
            features[75] = np.mean(confs)
            features[76] = np.std(confs)

        if len(self._total_obj_history) >= 3:
            objs = list(self._total_obj_history)
            features[77] = np.mean(objs)
            features[78] = np.std(objs)
            features[79] = objs[-1] - objs[0]

        if len(self._count_history) >= 2:
            c = list(self._count_history)
            features[80] = c[-1] - c[-2]

        if len(self._count_history) >= 5:
            recent = list(self._count_history)[-5:]
            features[81] = np.mean(recent)
            features[82] = np.std(recent)

        if person_objs and all_centers:
            for pi, p_obj in enumerate(person_objs[:2]):
                px = p_obj["center"][0] / w
                py = p_obj["center"][1] / h
                dists = [np.sqrt((px - cx)**2 + (py - cy)**2) for cx, cy in all_centers]
                min_dist = min(dists)
                features[86 + pi * 4] = min_dist
                features[87 + pi * 4] = 1.0 if min_dist < 0.2 else 0.0
                nearby = sum(1 for d in dists if d < 0.3)
                features[88 + pi * 4] = min(nearby / 5.0, 1.0)
                features[89 + pi * 4] = nearby

        if all_confs:
            features[94] = np.mean(all_confs)
            features[95] = np.std(all_confs)
            features[96] = np.median(all_confs)
            features[97] = np.max(all_confs)

        if all_sizes:
            features[98] = np.mean(all_sizes)
            features[99] = np.std(all_sizes)
            features[100] = np.median(all_sizes)

        total_obj_area = sum(
            o["bbox"][2] * o["bbox"][3]
            for objs in objects_by_class.values()
            for o in objs
        )
        features[101] = min(total_obj_area / (w * h * 0.3), 1.0)

        return features

    def extract_sequence_features(self, frames: list) -> np.ndarray:
        self.reset()
        features = []
        for i, frame in enumerate(frames):
            ff = self.extract_features(frame, frame_idx=i)
            features.append(ff.feature_vector)
        return np.array(features)

    def reset(self) -> None:
        self._count_history.clear()
        self._conf_history.clear()
        self._total_obj_history.clear()
