"""
Enhanced YOLO feature extractor with motion-aware sequence processing.

Feature vector (512 dims):
  0-49:    Person detection (count, positions, posture)
 50-99:    Person activity (standing vs bending, movement)
100-149:   Scene grid (4x4 = 16 cells x 3 dims)
150-199:   Object detection (5 classes x 10 dims)
200-249:   Motion features (optical flow, displacement, speed)
250-299:   Temporal stats (running averages, trends over sequence)
300-349:   ROI features (dip station bottom-right, cow rows)
350-511:   Visual features (brightness, color, edges per region)
"""

import logging
import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class Person:
    id: int
    bbox: Tuple[int, int, int, int]
    center: Tuple[int, int]
    confidence: float
    frame_seen: int


@dataclass
class FrameFeatures:
    num_persons: int
    persons: List[Person]
    feature_vector: np.ndarray


class EnhancedYOLODetector:
    def __init__(self, config):
        from ultralytics import YOLO

        self.config = config
        self.model = YOLO("yolov8n.pt")

        self.persons: List[Person] = []
        self.next_person_id = 0

        self.feature_size = 512

        self._prev_persons: List[Person] = []
        self._person_count_history: deque = deque(maxlen=30)
        self._person_conf_history: deque = deque(maxlen=30)
        self._person_center_history: deque = deque(maxlen=30)
        self._person_bbox_history: deque = deque(maxlen=30)

        self._class_names = self.model.names
        self._num_classes = len(self._class_names)

        logger.info(
            "EnhancedYOLODetector: loaded yolov8n.pt (%d classes, motion-aware)",
            self._num_classes,
        )

    def _assign_person_id(self, bbox, frame_idx):
        center = (bbox[0] + bbox[2] // 2, bbox[1] + bbox[3] // 2)
        min_dist = float("inf")
        best_id = None

        for person in self._prev_persons:
            if frame_idx - person.frame_seen > 5:
                continue
            prev_center = person.center
            dist = np.sqrt(
                (center[0] - prev_center[0]) ** 2
                + (center[1] - prev_center[1]) ** 2
            )
            if dist < min_dist and dist < 150:
                min_dist = dist
                best_id = person.id

        if best_id is not None:
            return best_id

        new_id = self.next_person_id
        self.next_person_id += 1
        return new_id

    def extract_features(self, frame: np.ndarray, frame_idx: int = 0) -> FrameFeatures:
        h_orig, w_orig = frame.shape[:2]
        results = self.model(
            frame,
            conf=self.config.yolo.confidence,
            imgsz=self.config.yolo.input_size,
            verbose=False,
        )

        persons = []
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

                if cls_id == 0:
                    person_id = self._assign_person_id(bbox, frame_idx)
                    person = Person(
                        id=person_id,
                        bbox=bbox,
                        center=center,
                        confidence=confidence,
                        frame_seen=frame_idx,
                    )
                    persons.append(person)
                else:
                    if cls_id not in objects_by_class:
                        objects_by_class[cls_id] = []
                    objects_by_class[cls_id].append(
                        {
                            "bbox": bbox,
                            "center": center,
                            "confidence": confidence,
                        }
                    )

        feature_vector = self._create_feature_vector(
            persons, objects_by_class, (h_orig, w_orig), frame
        )

        self._prev_persons = persons

        return FrameFeatures(
            num_persons=len(persons),
            persons=persons,
            feature_vector=feature_vector,
        )

    def _create_feature_vector(
        self,
        persons: List[Person],
        objects_by_class: Dict[int, list],
        frame_shape: Tuple[int, int],
        frame: np.ndarray,
    ) -> np.ndarray:
        h, w = frame_shape
        features = np.zeros(512)

        # === SECTION 1: Detection summary (0-19) ===
        total_objects = sum(len(v) for v in objects_by_class.values())
        avg_person_conf = (
            np.mean([p.confidence for p in persons]) if persons else 0.0
        )
        avg_obj_conf = 0.0
        if total_objects > 0:
            all_confs = [
                obj["confidence"]
                for objs in objects_by_class.values()
                for obj in objs
            ]
            avg_obj_conf = np.mean(all_confs)

        features[0] = min(len(persons) / 3.0, 1.0)
        features[1] = min(total_objects / 5.0, 1.0)
        features[2] = avg_person_conf
        features[3] = avg_obj_conf
        features[4] = len(persons)
        features[5] = total_objects

        self._person_count_history.append(len(persons))
        self._person_conf_history.append(avg_person_conf)
        if persons:
            cx = np.mean([p.center[0] for p in persons]) / w
            cy = np.mean([p.center[1] for p in persons]) / h
            self._person_center_history.append((cx, cy))
            avg_bh = np.mean([p.bbox[3] for p in persons])
            avg_bw = np.mean([p.bbox[2] for p in persons])
            self._person_bbox_history.append((avg_bw / w, avg_bh / h))
        else:
            self._person_center_history.append((0.5, 0.5))
            self._person_bbox_history.append((0.0, 0.0))

        if len(self._person_count_history) >= 2:
            counts = list(self._person_count_history)
            features[6] = counts[-1] - counts[-2]
            confs = list(self._person_conf_history)
            features[7] = confs[-1] - confs[-2]

        if len(self._person_center_history) >= 2:
            centers = list(self._person_center_history)
            dx = centers[-1][0] - centers[-2][0]
            dy = centers[-1][1] - centers[-2][1]
            features[8] = dx
            features[9] = dy
            features[10] = np.sqrt(dx**2 + dy**2)

        if len(self._person_count_history) >= 3:
            counts = list(self._person_count_history)
            features[11] = counts[-1] - counts[-3]

        # Person posture: standing (tall/narrow) vs bending (short/wide)
        if persons:
            aspect_ratios = []
            for p in persons:
                bw, bh = p.bbox[2], p.bbox[3]
                ar = bh / bw if bw > 0 else 1.0
                aspect_ratios.append(ar)
            avg_ar = np.mean(aspect_ratios)
            features[12] = min(avg_ar / 2.0, 1.0)  # normalized posture
            features[13] = 1.0 if avg_ar > 1.5 else 0.0  # standing flag

        # === SECTION 2: Person spatial (20-69) - 5 slots x 10 dims ===
        idx = 20
        for i, person in enumerate(persons[:5]):
            x, y, bw, bh = person.bbox
            cx, cy = person.center
            features[idx] = x / w
            features[idx + 1] = y / h
            features[idx + 2] = bw / w
            features[idx + 3] = bh / h
            features[idx + 4] = cx / w
            features[idx + 5] = cy / h
            features[idx + 6] = (bh / bw) if bw > 0 else 1.0
            features[idx + 7] = (bw * bh) / (w * h)
            features[idx + 8] = person.confidence
            features[idx + 9] = 1.0
            idx += 10

        # === SECTION 3: Scene grid (70-149) - 4x4 grid x 3 dims ===
        idx = 70
        grid_rows, grid_cols = 4, 4
        cell_h, cell_w = h // grid_rows, w // grid_cols
        for gr in range(grid_rows):
            for gc in range(grid_cols):
                y_start = gr * cell_h
                y_end = (gr + 1) * cell_h
                x_start = gc * cell_w
                x_end = (gc + 1) * cell_w
                cell_persons = []
                for p in persons:
                    px, py = p.center
                    if x_start <= px < x_end and y_start <= py < y_end:
                        cell_persons.append(p)
                features[idx] = min(len(cell_persons) / 2.0, 1.0)
                if cell_persons:
                    features[idx + 1] = np.mean(
                        [p.confidence for p in cell_persons]
                    )
                    features[idx + 2] = np.mean(
                        [p.center[1] / h for p in cell_persons]
                    )
                idx += 1

        # === SECTION 4: Object detection (150-199) ===
        idx = 150
        for cls_id in sorted(objects_by_class.keys())[:5]:
            objs = objects_by_class[cls_id]
            features[idx] = min(len(objs) / 3.0, 1.0)
            features[idx + 1] = np.mean([o["confidence"] for o in objs])
            features[idx + 2] = np.mean([o["bbox"][0] / w for o in objs])
            features[idx + 3] = np.mean([o["bbox"][1] / h for o in objs])
            features[idx + 4] = np.mean([o["bbox"][2] / w for o in objs])
            features[idx + 5] = np.mean([o["bbox"][3] / h for o in objs])
            features[idx + 6] = np.mean([o["center"][0] / w for o in objs])
            features[idx + 7] = np.mean([o["center"][1] / h for o in objs])
            features[idx + 8] = np.mean(
                [(o["bbox"][2] * o["bbox"][3]) / (w * h) for o in objs]
            )
            features[idx + 9] = 1.0
            idx += 10

        # === SECTION 5: Motion features (200-249) ===
        if persons and self._prev_persons:
            cur_centers = [p.center for p in persons]
            prev_centers = [p.center for p in self._prev_persons]
            best_dists = []
            for cc in cur_centers:
                min_d = min(
                    np.sqrt((cc[0] - pc[0]) ** 2 + (cc[1] - pc[1]) ** 2)
                    for pc in prev_centers
                )
                best_dists.append(min_d)
            features[200] = np.mean(best_dists) / max(w, h)
            features[201] = np.max(best_dists) / max(w, h)
            features[202] = len([d for d in best_dists if d < 30]) / max(
                len(cur_centers), 1
            )

            # Person displacement direction (horizontal vs vertical)
            if best_dists:
                dxs = []
                dys = []
                for cc in cur_centers:
                    closest_prev = min(prev_centers, key=lambda pc: np.sqrt(
                        (cc[0] - pc[0]) ** 2 + (cc[1] - pc[1]) ** 2
                    ))
                    dxs.append((cc[0] - closest_prev[0]) / w)
                    dys.append((cc[1] - closest_prev[1]) / h)
                features[203] = np.mean(np.abs(dxs))  # horizontal movement
                features[204] = np.mean(np.abs(dys))  # vertical movement
                features[205] = np.mean(dxs)  # net horizontal direction
                features[206] = np.mean(dys)  # net vertical direction

        new_ids = [p.id for p in persons if p.id not in [pp.id for pp in self._prev_persons]]
        lost_ids = [pp.id for pp in self._prev_persons if pp.id not in [p.id for p in persons]]
        features[207] = min(len(new_ids) / 2.0, 1.0)
        features[208] = min(len(lost_ids) / 2.0, 1.0)

        # === SECTION 6: Temporal running stats (250-299) ===
        if len(self._person_count_history) >= 3:
            counts = list(self._person_count_history)
            features[250] = np.mean(counts)
            features[251] = np.std(counts)
            features[252] = max(counts) - min(counts)
            features[253] = counts[-1]
            features[254] = counts[-1] - counts[0]
        if len(self._person_conf_history) >= 3:
            confs = list(self._person_conf_history)
            features[260] = np.mean(confs)
            features[261] = np.std(confs)
            features[262] = max(confs) - min(confs)
        if len(self._person_center_history) >= 3:
            centers = list(self._person_center_history)
            xs = [c[0] for c in centers]
            ys = [c[1] for c in centers]
            features[270] = np.mean(xs)
            features[271] = np.mean(ys)
            features[272] = np.std(xs)
            features[273] = np.std(ys)
            features[274] = xs[-1] - xs[0]
            features[275] = ys[-1] - ys[0]

            # Activity level: high variance = moving, low = stationary
            features[276] = np.std(xs) + np.std(ys)

        # === SECTION 7: ROI features (300-349) ===
        # Camera layout: dip station bottom-right, two cow rows parallel vertical
        if persons:
            for p in persons:
                px, py = p.center[0] / w, p.center[1] / h

                # At dip station (bottom-right)
                if px > 0.7 and py > 0.7:
                    features[300] = 1.0
                    features[301] = px
                    features[302] = py

                # At left cow row
                if px < 0.5:
                    features[303] = 1.0
                    features[304] = px
                    features[305] = py

                # At right cow row
                if px >= 0.5:
                    features[306] = 1.0
                    features[307] = px
                    features[308] = py

            # Person spread (how many rows they visit)
            all_cx = [p.center[0] / w for p in persons]
            features[310] = np.std(all_cx) if len(all_cx) > 1 else 0.0
            features[311] = max(all_cx) - min(all_cx) if all_cx else 0.0

        # Movement between ROIs over time
        if len(self._person_center_history) >= 5:
            centers = list(self._person_center_history)
            recent_xs = [c[0] for c in centers[-5:]]
            recent_ys = [c[1] for c in centers[-5:]]
            dip_count = sum(1 for x, y in zip(recent_xs, recent_ys) if x > 0.7 and y > 0.7)
            features[320] = dip_count / len(recent_xs)
            cow_count = sum(1 for x, y in zip(recent_xs, recent_ys) if y < 0.7)
            features[321] = cow_count / len(recent_xs)
            features[322] = np.std(recent_xs)

        # === SECTION 8: Action features (330-379) ===
        # These capture WHAT the person is DOING, not just WHERE they are

        if persons:
            px_mean = np.mean([p.center[0] / w for p in persons])
            py_mean = np.mean([p.center[1] / h for p in persons])

            # Person vertical zone (standing vs crouching near udder)
            # Cows are seen from side, udder is in lower half
            features[330] = py_mean  # 0=top, 1=bottom
            features[331] = 1.0 if py_mean > 0.6 else 0.0  # near ground/udder
            features[332] = 1.0 if py_mean < 0.4 else 0.0  # standing tall

            # Person horizontal zone (which cow row)
            features[333] = px_mean  # 0=left, 1=right
            features[334] = 1.0 if px_mean < 0.3 else 0.0  # far left
            features[335] = 1.0 if px_mean > 0.7 else 0.0  # far right (dip station)

            # Person movement speed (pixels per frame normalized)
            if len(self._person_center_history) >= 2:
                centers = list(self._person_center_history)
                dx = abs(centers[-1][0] - centers[-2][0])
                dy = abs(centers[-1][1] - centers[-2][1])
                speed = np.sqrt(dx**2 + dy**2)
                features[340] = min(speed * 10, 1.0)  # normalized speed
                features[341] = dx * 10  # horizontal speed
                features[342] = dy * 10  # vertical speed
                features[343] = 1.0 if speed > 0.02 else 0.0  # moving flag

            # Person posture change over time (bending vs standing)
            if len(self._person_bbox_history) >= 3:
                bboxes = list(self._person_bbox_history)
                ar_current = bboxes[-1][1] / max(bboxes[-1][0], 0.001)
                ar_prev = bboxes[-2][1] / max(bboxes[-2][0], 0.001)
                features[350] = ar_current  # current aspect ratio
                features[351] = ar_current - ar_prev  # posture change
                features[352] = 1.0 if ar_current < 1.2 else 0.0  # bending flag
                features[353] = 1.0 if ar_current > 1.8 else 0.0  # standing flag

            # Person-cow interaction (near cow udder vs walking)
            # Cow udder is typically at x>0.5, y>0.5 (right side, lower half)
            udder_dist = np.sqrt((px_mean - 0.75)**2 + (py_mean - 0.75)**2)
            features[360] = min(udder_dist, 1.0)  # distance to udder zone
            features[361] = 1.0 if udder_dist < 0.3 else 0.0  # near udder

            # Walking pattern: horizontal movement across frame
            if len(self._person_center_history) >= 5:
                centers = list(self._person_center_history)
                recent_xs = [c[0] for c in centers[-5:]]
                walking_range = max(recent_xs) - min(recent_xs)
                features[370] = walking_range  # how much person moves horizontally
                features[371] = 1.0 if walking_range > 0.3 else 0.0  # walking flag

        # === SECTION 9: Visual features (380-511) ===
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        features[380] = gray.mean() / 255.0
        features[381] = gray.std() / 128.0
        features[382] = gray.min() / 255.0
        features[383] = gray.max() / 255.0
        features[384] = hsv[:, :, 0].mean() / 180.0
        features[385] = hsv[:, :, 0].std() / 90.0
        features[386] = hsv[:, :, 1].mean() / 255.0
        features[387] = hsv[:, :, 1].std() / 128.0
        features[388] = hsv[:, :, 2].mean() / 255.0
        features[389] = hsv[:, :, 2].std() / 128.0

        idx = 390
        for ch in range(3):
            hist = cv2.calcHist([frame], [ch], None, [8], [0, 256])
            hist = hist.flatten() / (hist.sum() + 1e-7)
            features[idx : idx + 8] = hist
            idx += 8

        edges = cv2.Canny(gray, 50, 150)
        features[414] = edges.mean() / 255.0
        features[415] = edges.std() / 128.0

        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        features[416] = min(laplacian.var() / 10000.0, 1.0)

        h_g, w_g = gray.shape
        features[417] = gray[h_g // 2 :, :].mean() / 255.0
        features[418] = gray[: h_g // 2, :].mean() / 255.0
        features[419] = gray[:, : w_g // 2].mean() / 255.0
        features[420] = gray[:, w_g // 2 :].mean() / 255.0

        features[421] = gray[h_g // 2 :, :].std() / 128.0
        features[422] = gray[: h_g // 2, :].std() / 128.0
        features[423] = gray[:, : w_g // 2].std() / 128.0
        features[424] = gray[:, w_g // 2 :].std() / 128.0

        quadrants = [
            gray[: h_g // 2, : w_g // 2],
            gray[: h_g // 2, w_g // 2 :],
            gray[h_g // 2 :, : w_g // 2],
            gray[h_g // 2 :, w_g // 2 :],
        ]
        for qi, q in enumerate(quadrants):
            features[430 + qi * 4] = q.mean() / 255.0
            features[430 + qi * 4 + 1] = q.std() / 128.0
            q_edges = cv2.Canny(q, 50, 150)
            features[430 + qi * 4 + 2] = q_edges.mean() / 255.0
            features[430 + qi * 4 + 3] = q.std() / 128.0

        idx = 450
        dark_mask = (hsv[:, :, 2] < 80).astype(float)
        features[idx] = dark_mask.mean()
        features[idx + 1] = dark_mask.std()

        bright_mask = (hsv[:, :, 2] > 200).astype(float)
        features[idx + 2] = bright_mask.mean()
        features[idx + 3] = bright_mask.std()

        wet_mask = ((hsv[:, :, 1] > 50) & (hsv[:, :, 2] < 100)).astype(float)
        features[idx + 4] = wet_mask.mean()
        features[idx + 5] = wet_mask.std()

        idx = 460
        person_mask = np.zeros((h, w), dtype=np.uint8)
        for p in persons:
            x, y, bw, bh = p.bbox
            person_mask[y : y + bh, x : x + bw] = 255
        person_pixels = person_mask.sum() / 255.0
        features[idx] = min(person_pixels / (h * w * 0.3), 1.0)
        features[idx + 1] = np.sqrt(person_pixels) / max(h, w)

        if persons:
            all_cx = [p.center[0] for p in persons]
            all_cy = [p.center[1] for p in persons]
            features[idx + 2] = np.mean(all_cx) / w
            features[idx + 3] = np.mean(all_cy) / h
            if len(persons) > 1:
                features[idx + 4] = np.std(all_cx) / w
                features[idx + 5] = np.std(all_cy) / h

        return features

    def extract_sequence_features(
        self, frames: List[np.ndarray]
    ) -> np.ndarray:
        self.reset()
        sequence_features = []
        for i, frame in enumerate(frames):
            frame_features = self.extract_features(frame, frame_idx=i)
            sequence_features.append(frame_features.feature_vector)
        return np.array(sequence_features)

    def reset(self) -> None:
        self.persons = []
        self._prev_persons = []
        self.next_person_id = 0
        self._person_count_history.clear()
        self._person_conf_history.clear()
        self._person_center_history.clear()
        self._person_bbox_history.clear()
