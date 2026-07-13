"""
Enhanced YOLO feature extractor with multi-person tracking and spatial awareness.
"""

import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class Person:
    """Tracked person with ID."""
    id: int
    bbox: Tuple[int, int, int, int]
    center: Tuple[int, int]
    confidence: float
    frame_seen: int
    arm_raised: bool = False
    near_station: bool = False
    holding_object: bool = False


@dataclass
class SpatialRegion:
    """Region of interest in the frame."""
    name: str
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    purpose: str


@dataclass
class FrameFeatures:
    """Enhanced features from a single frame."""
    # Person tracking
    num_persons: int
    persons: List[Person]
    primary_person: Optional[Person]  # Person performing task
    
    # Spatial features
    person_in_roi: Dict[str, bool]  # ROI name -> person present
    persons_near_station: int
    
    # Action features
    arm_raised_detected: bool
    pipe_detected: bool
    cup_fill_detected: bool
    
    # Object features
    spray_bottle: bool
    stripping_cup: bool
    teat_cups_attached: bool
    teat_cups_detached: bool
    dip_applicator: bool
    dip_station: bool
    
    # Feature vector (512 dims)
    feature_vector: np.ndarray


class EnhancedYOLODetector:
    """
    Enhanced YOLO detector with multi-person tracking and domain knowledge.
    """
    
    def __init__(self, config):
        """
        Initialize the enhanced detector.
        
        Args:
            config: Configuration with domain knowledge
        """
        from ultralytics import YOLO

        self.config = config
        # Always use default yolov8n.pt for person detection
        self.model = YOLO("yolov8n.pt")
        
        # Known spatial regions (from config)
        self.regions = {
            "dip_station": SpatialRegion(
                name="dip_station",
                bbox=tuple(config.domain.stations.dip_station),
                purpose="Cup filling station"
            ),
            "milking_area": SpatialRegion(
                name="milking_area",
                bbox=(0.2, 0.0, 0.6, 1.0),  # Center area
                purpose="Main milking area"
            )
        }
        
        # Person tracking
        self.persons: List[Person] = []
        self.next_person_id = 0
        self.person_history: Dict[int, deque] = {}
        
        # Feature size
        self.feature_size = 512
    
    def _assign_person_id(self, bbox: Tuple[int, int, int, int], frame_idx: int) -> int:
        """
        Assign ID to detected person based on proximity to previous detections.
        
        Args:
            bbox: Bounding box (x, y, w, h)
            frame_idx: Current frame index
        
        Returns:
            Person ID
        """
        center = (bbox[0] + bbox[2] // 2, bbox[1] + bbox[3] // 2)
        
        # Find closest person from previous frame
        min_dist = float('inf')
        best_id = None
        
        for person in self.persons:
            if frame_idx - person.frame_seen > 5:  # Lost tracking
                continue
            
            prev_center = person.center
            dist = np.sqrt((center[0] - prev_center[0])**2 + 
                          (center[1] - prev_center[1])**2)
            
            if dist < min_dist and dist < 100:  # Max movement threshold
                min_dist = dist
                best_id = person.id
        
        if best_id is not None:
            return best_id
        
        # New person
        new_id = self.next_person_id
        self.next_person_id += 1
        return new_id
    
    def _analyze_person_actions(self, person: Person, frame: np.ndarray, detections: List) -> Person:
        """
        Analyze what a person is doing.
        
        Args:
            person: Person object
            frame: Current frame
            detections: YOLO detections
        
        Returns:
            Updated Person object
        """
        h, w = frame.shape[:2]
        
        # Check if arm is raised (simple heuristic: person bbox aspect ratio)
        x, y, bw, bh = person.bbox
        aspect_ratio = bh / bw if bw > 0 else 1.0
        
        # Raised arm makes person taller/narrower
        person.arm_raised = aspect_ratio > 1.5
        
        # Check if near dip station (bottom-left)
        station_bbox = self.regions["dip_station"].bbox
        sx, sy, sw, sh = station_bbox
        sx_abs, sy_abs = int(sx * w), int(sy * h)
        sw_abs, sh_abs = int(sw * w), int(sh * h)
        
        person.near_station = (
            sx_abs <= person.center[0] <= sx_abs + sw_abs and
            sy_abs <= person.center[1] <= sy_abs + sh_abs
        )
        
        return person
    
    def _check_roi_presence(self, persons: List[Person], frame_shape: Tuple[int, int]) -> Dict[str, bool]:
        """
        Check which ROIs have persons.
        
        Args:
            persons: List of detected persons
            frame_shape: (height, width)
        
        Returns:
            Dict mapping ROI name to presence
        """
        h, w = frame_shape[:2]
        roi_presence = {}
        
        for roi_name, region in self.regions.items():
            rx, ry, rw, rh = region.bbox
            rx_abs, ry_abs = int(rx * w), int(ry * h)
            rw_abs, rh_abs = int(rw * w), int(rh * h)
            
            has_person = False
            for person in persons:
                if (rx_abs <= person.center[0] <= rx_abs + rw_abs and
                    ry_abs <= person.center[1] <= ry_abs + rh_abs):
                    has_person = True
                    break
            
            roi_presence[roi_name] = has_person
        
        return roi_presence
    
    def extract_features(self, frame: np.ndarray, frame_idx: int = 0) -> FrameFeatures:
        """
        Extract enhanced features from a frame.

        Args:
            frame: BGR image
            frame_idx: Frame index for tracking

        Returns:
            FrameFeatures with all extracted information
        """
        # Run YOLO with larger input size for better small-person detection
        h_orig, w_orig = frame.shape[:2]
        results = self.model(frame, conf=self.config.yolo.confidence, imgsz=1280, verbose=False)

        h, w = h_orig, w_orig
        
        # Extract persons
        persons = []
        objects = []
        
        for result in results:
            if result.boxes is None:
                continue
            
            for box in result.boxes:
                cls_id = int(box.cls.item())
                confidence = float(box.conf.item())
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                
                bbox = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                center = (int((x1 + x2) / 2), int((y1 + y2) / 2))
                
                if cls_id == 0:  # Person
                    person_id = self._assign_person_id(bbox, frame_idx)
                    person = Person(
                        id=person_id,
                        bbox=bbox,
                        center=center,
                        confidence=confidence,
                        frame_seen=frame_idx
                    )
                    person = self._analyze_person_actions(person, frame, results)
                    persons.append(person)
                else:
                    objects.append({
                        "class_id": cls_id,
                        "class_name": self.model.names.get(cls_id, f"class_{cls_id}"),
                        "confidence": confidence,
                        "bbox": bbox,
                        "center": center
                    })
        
        # Analyze spatial presence
        roi_presence = self._check_roi_presence(persons, (h, w))
        persons_near_station = sum(1 for p in persons if p.near_station)
        
        # Detect specific objects
        object_names = [o["class_name"] for o in objects]
        
        # Create feature vector
        feature_vector = self._create_enhanced_feature_vector(
            persons, objects, roi_presence, (h, w), persons_near_station, frame
        )
        
        # Determine primary person (closest to milking area)
        primary_person = None
        if persons:
            milking_center = (w // 2, h // 2)
            min_dist = float('inf')
            for p in persons:
                dist = np.sqrt((p.center[0] - milking_center[0])**2 + 
                              (p.center[1] - milking_center[1])**2)
                if dist < min_dist:
                    min_dist = dist
                    primary_person = p
        
        return FrameFeatures(
            num_persons=len(persons),
            persons=persons,
            primary_person=primary_person,
            person_in_roi=roi_presence,
            persons_near_station=persons_near_station,
            arm_raised_detected=any(p.arm_raised for p in persons),
            pipe_detected="pipe" in object_names or "hose" in object_names,
            cup_fill_detected=persons_near_station > 0 and any(p.near_station for p in persons),
            spray_bottle="spray_bottle" in object_names,
            stripping_cup="stripping_cup" in object_names,
            teat_cups_attached="teat_cups_attached" in object_names,
            teat_cups_detached="teat_cups_detached" in object_names,
            dip_applicator="dip_applicator" in object_names,
            dip_station=roi_presence.get("dip_station", False),
            feature_vector=feature_vector
        )
    
    def _create_enhanced_feature_vector(
        self,
        persons: List[Person],
        objects: List[dict],
        roi_presence: Dict[str, bool],
        frame_shape: Tuple[int, int],
        persons_near_station: int = 0,
        frame: np.ndarray = None
    ) -> np.ndarray:
        """
        Create enhanced 512-dim feature vector.

        Args:
            persons: Detected persons
            objects: Detected objects
            roi_presence: ROI presence flags
            frame_shape: (height, width)
            persons_near_station: Number of persons near station
            frame: Original BGR frame for visual features

        Returns:
            512-dim feature vector
        """
        h, w = frame_shape
        features = np.zeros(512)
        idx = 0
        
        # === Person features (0-99) ===
        features[idx] = min(len(persons) / 3.0, 1.0)  # Normalized count
        idx += 1
        
        for i, person in enumerate(persons[:3]):  # Max 3 persons
            if idx + 10 > 100:
                break
            
            # Normalized bbox
            x, y, bw, bh = person.bbox
            features[idx:idx+4] = [x/w, y/h, bw/w, bh/h]
            idx += 4
            
            # Normalized center
            cx, cy = person.center
            features[idx:idx+2] = [cx/w, cy/h]
            idx += 2
            
            # Action flags
            features[idx] = 1.0 if person.arm_raised else 0.0
            features[idx+1] = 1.0 if person.near_station else 0.0
            features[idx+2] = person.confidence
            idx += 3
        
        idx = 100  # Skip to next section
        
        # === Spatial features (100-149) ===
        for roi_name, present in roi_presence.items():
            if idx >= 150:
                break
            features[idx] = 1.0 if present else 0.0
            idx += 1
        
        features[idx] = min(persons_near_station / 2.0, 1.0)
        idx += 1
        
        idx = 150  # Skip to next section
        
        # === Action features (150-199) ===
        features[idx] = 1.0 if any(p.arm_raised for p in persons) else 0.0  # arm_raised
        features[idx+1] = 1.0 if persons_near_station > 0 else 0.0  # near_station
        features[idx+2] = 1.0 if any(p.holding_object for p in persons) else 0.0
        idx += 3
        
        idx = 200  # Skip to next section
        
        # === Object features (200-249) ===
        object_flags = [
            ("spray_bottle", 200),
            ("stripping_cup", 201),
            ("teat_cups_attached", 202),
            ("teat_cups_detached", 203),
            ("dip_applicator", 204),
        ]
        
        object_names = [o["class_name"] for o in objects]
        for obj_name, feat_idx in object_flags:
            features[feat_idx] = 1.0 if obj_name in object_names else 0.0
        
        idx = 250  # Skip to next section
        
        # === Temporal features (250-299) ===
        # Placeholder for motion vectors (computed across frames)
        
        idx = 300  # Skip to next section
        
        # === Relationship features (300-349) ===
        if persons:
            person = persons[0]  # Primary person
            for obj in objects[:5]:
                if idx + 3 >= 350:
                    break
                # Distance from person to object
                dx = (obj["center"][0] - person.center[0]) / w
                dy = (obj["center"][1] - person.center[1]) / h
                dist = np.sqrt(dx**2 + dy**2)
                features[idx:idx+3] = [dx, dy, dist]
                idx += 3

        idx = 350  # Skip to next section

        # === Frame-level visual features (350-511) ===
        if frame is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # Brightness stats (350-353)
            features[idx] = gray.mean() / 255.0
            features[idx+1] = gray.std() / 128.0
            features[idx+2] = gray.min() / 255.0
            features[idx+3] = gray.max() / 255.0
            idx += 4

            # HSV stats (354-359)
            features[idx] = hsv[:,:,0].mean() / 180.0
            features[idx+1] = hsv[:,:,0].std() / 90.0
            features[idx+2] = hsv[:,:,1].mean() / 255.0
            features[idx+3] = hsv[:,:,1].std() / 128.0
            features[idx+4] = hsv[:,:,2].mean() / 255.0
            features[idx+5] = hsv[:,:,2].std() / 128.0
            idx += 6

            # Color histograms - BGR (360-383, 8 bins per channel)
            for ch in range(3):
                hist = cv2.calcHist([frame], [ch], None, [8], [0, 256])
                hist = hist.flatten() / (hist.sum() + 1e-7)
                features[idx:idx+8] = hist
                idx += 8

            # Edge density (384-387)
            edges = cv2.Canny(gray, 50, 150)
            features[idx] = edges.mean() / 255.0
            features[idx+1] = edges.std() / 128.0
            idx += 2

            # Texture - Laplacian variance (388-389)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            features[idx] = min(laplacian.var() / 10000.0, 1.0)
            idx += 1

            # Region brightness - bottom half vs top half (390-391)
            h_g, w_g = gray.shape
            features[idx] = gray[h_g//2:, :].mean() / 255.0
            features[idx+1] = gray[:h_g//2, :].mean() / 255.0
            idx += 2

            # Region brightness - left vs right (392-393)
            features[idx] = gray[:, :w_g//2].mean() / 255.0
            features[idx+1] = gray[:, w_g//2:].mean() / 255.0
            idx += 2

            # Water/moisture detection - high saturation + low value regions (394-395)
            # Wet floors appear dark and reflective
            dark_mask = (hsv[:,:,2] < 80).astype(float)
            features[idx] = dark_mask.mean()
            features[idx+1] = dark_mask.std()
            idx += 2

        return features
    
    def extract_sequence_features(
        self,
        frames: List[np.ndarray]
    ) -> np.ndarray:
        """
        Extract features from a sequence of frames.
        
        Args:
            frames: List of BGR images
        
        Returns:
            numpy array of shape (sequence_length, 512)
        """
        sequence_features = []
        
        for i, frame in enumerate(frames):
            frame_features = self.extract_features(frame, frame_idx=i)
            sequence_features.append(frame_features.feature_vector)
        
        return np.array(sequence_features)
