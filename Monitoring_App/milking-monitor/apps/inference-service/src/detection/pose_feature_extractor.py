"""
Pose-based feature extractor using YOLOv8-Pose.

Detects person + 17 keypoints (COCO format):
  - Arms: shoulder, elbow, wrist (left/right)
  - Used to detect: arm raise, working posture, row position

Feature vector (512 dims):
  0-49:    Person detection (count, positions)
  50-99:   Arm pose features (raise, left/right arm, both arms)
 100-149:  Row position (left/right cow row, dip station)
 150-199:  Keypoint positions (normalized)
 200-249:  Motion features (displacement, speed)
 250-299:  Temporal stats (running averages)
 300-349:  Action features (walking, working, bending)
 350-511:  Scene/visual features
"""

import logging
import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)

# COCO keypoint indices
NOSE = 0
LEFT_EYE = 1
RIGHT_EYE = 2
LEFT_EAR = 3
RIGHT_EAR = 4
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW = 7
RIGHT_ELBOW = 8
LEFT_WRIST = 9
RIGHT_WRIST = 10
LEFT_HIP = 11
RIGHT_HIP = 12
LEFT_KNEE = 13
RIGHT_KNEE = 14
LEFT_ANKLE = 15
RIGHT_ANKLE = 16


@dataclass
class PosePerson:
    id: int
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    center: Tuple[int, int]
    confidence: float
    keypoints: np.ndarray  # (17, 3) - x, y, confidence
    frame_seen: int
    left_arm_raised: bool = False
    right_arm_raised: bool = False
    row: str = "center"  # "left", "right", "center", "dip"


@dataclass
class PoseFrameFeatures:
    num_persons: int
    persons: List[PosePerson]
    feature_vector: np.ndarray


class PoseFeatureExtractor:
    def __init__(self, config):
        from ultralytics import YOLO

        self.config = config
        # Load YOLOv8-Pose model
        self.model = YOLO("yolov8n-pose.pt")

        self.persons: List[PosePerson] = []
        self.next_person_id = 0

        self.feature_size = 512

        self._prev_persons: List[PosePerson] = []
        self._person_count_history: deque = deque(maxlen=30)
        self._person_center_history: deque = deque(maxlen=30)
        self._arm_raise_history: deque = deque(maxlen=30)  # (left_raised, right_raised)
        self._row_history: deque = deque(maxlen=30)  # which row person is in

        logger.info("PoseFeatureExtractor: loaded yolov8n-pose.pt")

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

    def _detect_arm_raise(self, keypoints: np.ndarray, person_bbox: Tuple[int, int, int, int]) -> Tuple[bool, bool]:
        """Detect if left/right arm is extended (working posture).
        
        Camera looks DOWN from high angle. When person works on cow:
        - Arm extends FORWARD toward cow (wrist.y > shoulder.y in image coords)
        - Wrist is far from body center horizontally
        
        We detect "arm extended" = wrist.y > shoulder.y + threshold
        AND wrist.x is far from body center (not hanging at side).
        """
        _, _, _, person_h = person_bbox
        threshold = person_h * 0.05

        left_raised = False
        right_raised = False

        # Body center (midpoint of hips)
        if keypoints[LEFT_HIP, 2] > 0.3 and keypoints[RIGHT_HIP, 2] > 0.3:
            body_cx = (keypoints[LEFT_HIP, 0] + keypoints[RIGHT_HIP, 0]) / 2
        else:
            body_cx = (keypoints[LEFT_SHOULDER, 0] + keypoints[RIGHT_SHOULDER, 0]) / 2 if keypoints[LEFT_SHOULDER, 2] > 0.3 else 0

        # Left arm: shoulder(5) -> elbow(7) -> wrist(9)
        if (keypoints[LEFT_SHOULDER, 2] > 0.3 and
            keypoints[LEFT_ELBOW, 2] > 0.3 and
            keypoints[LEFT_WRIST, 2] > 0.3):
            shoulder_y = keypoints[LEFT_SHOULDER, 1]
            wrist_y = keypoints[LEFT_WRIST, 1]
            wrist_x = keypoints[LEFT_WRIST, 0]
            # Arm extended forward (wrist below shoulder in image = toward cow)
            forward = wrist_y > shoulder_y + threshold
            # Arm away from body (horizontal distance)
            away = abs(wrist_x - body_cx) > person_h * 0.15
            left_raised = forward and away

        # Right arm: shoulder(6) -> elbow(8) -> wrist(10)
        if (keypoints[RIGHT_SHOULDER, 2] > 0.3 and
            keypoints[RIGHT_ELBOW, 2] > 0.3 and
            keypoints[RIGHT_WRIST, 2] > 0.3):
            shoulder_y = keypoints[RIGHT_SHOULDER, 1]
            wrist_y = keypoints[RIGHT_WRIST, 1]
            wrist_x = keypoints[RIGHT_WRIST, 0]
            forward = wrist_y > shoulder_y + threshold
            away = abs(wrist_x - body_cx) > person_h * 0.15
            right_raised = forward and away

        return left_raised, right_raised

    def _detect_row(self, center_x: int, frame_w: int) -> str:
        """Detect which row the person is in based on x position.
        
        Camera layout:
        - Left cow row: x < 0.4
        - Center aisle: 0.4 <= x <= 0.6
        - Right cow row: x > 0.6
        - Dip station: x > 0.75 and y > 0.7
        """
        x_ratio = center_x / frame_w

        if x_ratio < 0.4:
            return "left"
        elif x_ratio > 0.6:
            if x_ratio > 0.75:
                return "dip"
            return "right"
        else:
            return "center"

    def extract_features(self, frame: np.ndarray, frame_idx: int = 0) -> PoseFrameFeatures:
        h_orig, w_orig = frame.shape[:2]
        results = self.model(
            frame,
            conf=self.config.yolo.confidence,
            imgsz=self.config.yolo.input_size,
            verbose=False,
        )

        persons = []

        for result in results:
            if result.keypoints is None:
                continue

            for i, (box, kpts) in enumerate(zip(result.boxes, result.keypoints)):
                cls_id = int(box.cls.item())
                if cls_id != 0:  # Only persons
                    continue

                confidence = float(box.conf.item())
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                bbox = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                center = (int((x1 + x2) / 2), int((y1 + y2) / 2))

                # Get keypoints (17, 3) - x, y, confidence
                kps = kpts.data[0].cpu().numpy()  # (17, 3)

                # Detect arm raise
                left_raised, right_raised = self._detect_arm_raise(kps, bbox)

                # Detect row
                row = self._detect_row(center[0], w_orig)

                person_id = self._assign_person_id(bbox, frame_idx)
                person = PosePerson(
                    id=person_id,
                    bbox=bbox,
                    center=center,
                    confidence=confidence,
                    keypoints=kps,
                    frame_seen=frame_idx,
                    left_arm_raised=left_raised,
                    right_arm_raised=right_raised,
                    row=row,
                )
                persons.append(person)

        feature_vector = self._create_feature_vector(
            persons, (h_orig, w_orig), frame
        )

        self._prev_persons = persons

        return PoseFrameFeatures(
            num_persons=len(persons),
            persons=persons,
            feature_vector=feature_vector,
        )

    def _create_feature_vector(
        self,
        persons: List[PosePerson],
        frame_shape: Tuple[int, int],
        frame: np.ndarray,
    ) -> np.ndarray:
        h, w = frame_shape
        features = np.zeros(512)

        # === SECTION 1: Person detection (0-49) ===
        features[0] = min(len(persons) / 3.0, 1.0)
        features[1] = len(persons)

        self._person_count_history.append(len(persons))

        if persons:
            cx = np.mean([p.center[0] for p in persons]) / w
            cy = np.mean([p.center[1] for p in persons]) / h
            self._person_center_history.append((cx, cy))
        else:
            self._person_center_history.append((0.5, 0.5))

        if len(self._person_count_history) >= 2:
            counts = list(self._person_count_history)
            features[2] = counts[-1] - counts[-2]

        if len(self._person_center_history) >= 2:
            centers = list(self._person_center_history)
            dx = centers[-1][0] - centers[-2][0]
            dy = centers[-1][1] - centers[-2][1]
            features[3] = dx
            features[4] = dy
            features[5] = np.sqrt(dx**2 + dy**2)

        # Person spatial info
        idx = 10
        for i, person in enumerate(persons[:5]):
            x, y, bw, bh = person.bbox
            cx, cy = person.center
            features[idx] = x / w
            features[idx + 1] = y / h
            features[idx + 2] = bw / w
            features[idx + 3] = bh / h
            features[idx + 4] = cx / w
            features[idx + 5] = cy / h
            features[idx + 6] = person.confidence
            features[idx + 7] = 1.0
            idx += 10

        # === SECTION 2: Arm pose features (50-99) ===
        if persons:
            # Count raised arms
            left_raised_count = sum(1 for p in persons if p.left_arm_raised)
            right_raised_count = sum(1 for p in persons if p.right_arm_raised)
            any_raised = sum(1 for p in persons if p.left_arm_raised or p.right_arm_raised)
            both_raised = sum(1 for p in persons if p.left_arm_raised and p.right_arm_raised)

            features[50] = min(left_raised_count / 2.0, 1.0)
            features[51] = min(right_raised_count / 2.0, 1.0)
            features[52] = min(any_raised / 2.0, 1.0)
            features[53] = min(both_raised / 2.0, 1.0)

            # Arm raise ratio (what % of detected persons have arms raised)
            features[54] = any_raised / max(len(persons), 1)

            # Track arm raise history
            if persons:
                p = persons[0]  # primary person
                self._arm_raise_history.append((p.left_arm_raised, p.right_arm_raised))

            # Arm raise pattern over time
            if len(self._arm_raise_history) >= 3:
                history = list(self._arm_raise_history)
                left_count = sum(1 for lr, rr in history if lr)
                right_count = sum(1 for lr, rr in history if rr)
                features[55] = left_count / len(history)
                features[56] = right_count / len(history)
                features[57] = (left_count + right_count) / (2 * len(history))

            # Arm positions (normalized keypoints)
            idx = 60
            for person in persons[:3]:
                kps = person.keypoints
                # Left arm: shoulder(5), elbow(7), wrist(9)
                if kps[LEFT_SHOULDER, 2] > 0.3:
                    features[idx] = kps[LEFT_SHOULDER, 0] / w
                    features[idx + 1] = kps[LEFT_SHOULDER, 1] / h
                if kps[LEFT_ELBOW, 2] > 0.3:
                    features[idx + 2] = kps[LEFT_ELBOW, 0] / w
                    features[idx + 3] = kps[LEFT_ELBOW, 1] / h
                if kps[LEFT_WRIST, 2] > 0.3:
                    features[idx + 4] = kps[LEFT_WRIST, 0] / w
                    features[idx + 5] = kps[LEFT_WRIST, 1] / h

                # Right arm: shoulder(6), elbow(8), wrist(10)
                if kps[RIGHT_SHOULDER, 2] > 0.3:
                    features[idx + 6] = kps[RIGHT_SHOULDER, 0] / w
                    features[idx + 7] = kps[RIGHT_SHOULDER, 1] / h
                if kps[RIGHT_ELBOW, 2] > 0.3:
                    features[idx + 8] = kps[RIGHT_ELBOW, 0] / w
                    features[idx + 9] = kps[RIGHT_ELBOW, 1] / h

                idx += 10

        # === SECTION 3: Row position (100-149) ===
        if persons:
            # Count persons in each row
            left_count = sum(1 for p in persons if p.row == "left")
            right_count = sum(1 for p in persons if p.row == "right")
            center_count = sum(1 for p in persons if p.row == "center")
            dip_count = sum(1 for p in persons if p.row == "dip")

            features[100] = min(left_count / 2.0, 1.0)
            features[101] = min(right_count / 2.0, 1.0)
            features[102] = min(center_count / 2.0, 1.0)
            features[103] = min(dip_count / 2.0, 1.0)

            # Primary person's row
            p = persons[0]
            features[104] = 1.0 if p.row == "left" else 0.0
            features[105] = 1.0 if p.row == "right" else 0.0
            features[106] = 1.0 if p.row == "center" else 0.0
            features[107] = 1.0 if p.row == "dip" else 0.0

            # Row movement history
            self._row_history.append(p.row)
            if len(self._row_history) >= 5:
                history = list(self._row_history)[-5:]
                features[108] = history.count("left") / len(history)
                features[109] = history.count("right") / len(history)
                features[110] = history.count("center") / len(history)
                features[111] = history.count("dip") / len(history)

                # Row switching (person moves between rows)
                row_changes = sum(1 for i in range(1, len(history)) if history[i] != history[i-1])
                features[112] = min(row_changes / 3.0, 1.0)

        # === SECTION 4: Keypoint positions (150-199) ===
        if persons:
            p = persons[0]  # primary person
            kps = p.keypoints

            # Normalize all 17 keypoints
            for i in range(17):
                if kps[i, 2] > 0.3:  # confidence threshold
                    features[150 + i * 2] = kps[i, 0] / w
                    features[150 + i * 2 + 1] = kps[i, 1] / h

            # Head position (nose)
            if kps[NOSE, 2] > 0.3:
                features[184] = kps[NOSE, 0] / w
                features[185] = kps[NOSE, 1] / h

            # Body center (midpoint of hips)
            if kps[LEFT_HIP, 2] > 0.3 and kps[RIGHT_HIP, 2] > 0.3:
                body_cx = (kps[LEFT_HIP, 0] + kps[RIGHT_HIP, 0]) / 2
                body_cy = (kps[LEFT_HIP, 1] + kps[RIGHT_HIP, 1]) / 2
                features[186] = body_cx / w
                features[187] = body_cy / h

            # Arm angles (shoulder-elbow-wrist)
            if (kps[LEFT_SHOULDER, 2] > 0.3 and
                kps[LEFT_ELBOW, 2] > 0.3 and
                kps[LEFT_WRIST, 2] > 0.3):
                # Left arm angle
                dx1 = kps[LEFT_ELBOW, 0] - kps[LEFT_SHOULDER, 0]
                dy1 = kps[LEFT_ELBOW, 1] - kps[LEFT_SHOULDER, 1]
                dx2 = kps[LEFT_WRIST, 0] - kps[LEFT_ELBOW, 0]
                dy2 = kps[LEFT_WRIST, 1] - kps[LEFT_ELBOW, 1]
                angle = np.arctan2(dy2, dx2) - np.arctan2(dy1, dx1)
                features[188] = (angle + np.pi) / (2 * np.pi)  # normalize to [0, 1]

            if (kps[RIGHT_SHOULDER, 2] > 0.3 and
                kps[RIGHT_ELBOW, 2] > 0.3 and
                kps[RIGHT_WRIST, 2] > 0.3):
                # Right arm angle
                dx1 = kps[RIGHT_ELBOW, 0] - kps[RIGHT_SHOULDER, 0]
                dy1 = kps[RIGHT_ELBOW, 1] - kps[RIGHT_SHOULDER, 1]
                dx2 = kps[RIGHT_WRIST, 0] - kps[RIGHT_ELBOW, 0]
                dy2 = kps[RIGHT_WRIST, 1] - kps[RIGHT_ELBOW, 1]
                angle = np.arctan2(dy2, dx2) - np.arctan2(dy1, dy1)
                features[189] = (angle + np.pi) / (2 * np.pi)

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
            features[202] = len([d for d in best_dists if d < 30]) / max(len(cur_centers), 1)

            # Displacement direction
            if best_dists:
                dxs = []
                dys = []
                for cc in cur_centers:
                    closest_prev = min(prev_centers, key=lambda pc: np.sqrt(
                        (cc[0] - pc[0]) ** 2 + (cc[1] - pc[1]) ** 2
                    ))
                    dxs.append((cc[0] - closest_prev[0]) / w)
                    dys.append((cc[1] - closest_prev[1]) / h)
                features[203] = np.mean(np.abs(dxs))
                features[204] = np.mean(np.abs(dys))
                features[205] = np.mean(dxs)
                features[206] = np.mean(dys)

        # === SECTION 6: Temporal stats (250-299) ===
        if len(self._person_count_history) >= 3:
            counts = list(self._person_count_history)
            features[250] = np.mean(counts)
            features[251] = np.std(counts)
            features[252] = max(counts) - min(counts)

        if len(self._person_center_history) >= 3:
            centers = list(self._person_center_history)
            xs = [c[0] for c in centers]
            ys = [c[1] for c in centers]
            features[260] = np.mean(xs)
            features[261] = np.mean(ys)
            features[262] = np.std(xs)
            features[263] = np.std(ys)
            features[264] = xs[-1] - xs[0]
            features[265] = ys[-1] - ys[0]
            features[266] = np.std(xs) + np.std(ys)

        if len(self._arm_raise_history) >= 3:
            history = list(self._arm_raise_history)
            left_count = sum(1 for lr, rr in history if lr)
            right_count = sum(1 for lr, rr in history if rr)
            features[270] = left_count / len(history)
            features[271] = right_count / len(history)
            features[272] = (left_count + right_count) / (2 * len(history))

        # === SECTION 7: Action features (300-349) ===
        if persons:
            p = persons[0]
            px, py = p.center[0] / w, p.center[1] / h

            # Walking vs working
            if len(self._person_center_history) >= 5:
                centers = list(self._person_center_history)
                recent_xs = [c[0] for c in centers[-5:]]
                recent_ys = [c[1] for c in centers[-5:]]
                walking_range = max(recent_xs) - min(recent_xs)
                features[300] = walking_range
                features[301] = 1.0 if walking_range > 0.3 else 0.0

                # Working (stationary + arms raised)
                is_stationary = walking_range < 0.1
                has_raised = p.left_arm_raised or p.right_arm_raised
                features[302] = 1.0 if (is_stationary and has_raised) else 0.0

            # Person vertical position (bending vs standing)
            features[310] = py
            features[311] = 1.0 if py > 0.6 else 0.0  # near ground
            features[312] = 1.0 if py < 0.4 else 0.0  # standing tall

            # At dip station
            features[320] = 1.0 if p.row == "dip" else 0.0

            # Row activity
            features[330] = 1.0 if p.row == "left" else 0.0
            features[331] = 1.0 if p.row == "right" else 0.0

        # === SECTION 8: Visual features (350-511) ===
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        features[350] = gray.mean() / 255.0
        features[351] = gray.std() / 128.0
        features[352] = hsv[:, :, 0].mean() / 180.0
        features[353] = hsv[:, :, 1].mean() / 255.0
        features[354] = hsv[:, :, 2].mean() / 255.0

        # Person region features
        if persons:
            person_mask = np.zeros((h, w), dtype=np.uint8)
            for p in persons:
                x, y, bw, bh = p.bbox
                person_mask[y:y+bh, x:x+bw] = 255
            person_pixels = person_mask.sum() / 255.0
            features[360] = min(person_pixels / (h * w * 0.3), 1.0)

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
        self._person_center_history.clear()
        self._arm_raise_history.clear()
        self._row_history.clear()
