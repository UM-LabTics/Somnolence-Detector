import math
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

from ear import LEFT_EYE, RIGHT_EYE, compute_ear
from geometry import dist, iou
from head_pose import estimate_head_pose
from mar import compute_mar
from perclos import PerclosTracker
from phone_detector import (
    LEFT_EAR_IDX,
    RIGHT_EAR_IDX,
    HandDetector,
    compute_min_hand_ear_distance,
    hand_bbox_from_landmarks,
)
from yolo_phone_detector import create_yolo_worker

# Default configuration
DEFAULT_CONFIG = {
    # EAR / PERCLOS
    "ear_threshold": 0.21,
    "perclos_window_seconds": 60.0,
    "perclos_low_threshold": 0.15,
    "perclos_medium_threshold": 0.25,
    "perclos_high_threshold": 0.40,
    # MAR / Yawn
    "mar_threshold": 0.55,
    "yawn_consec_frames": 30,  # ~1s at 30fps
    # Head pose / Nod
    "pitch_threshold": 150.0,  # degrees; see _check_head_nod for semantics
    "nod_consec_frames": 25,  # ~0.8s at 30fps
    "nod_sustained_frames": 75,  # ~2.5s for HIGH
    # MediaPipe
    "max_num_faces": 1,
    "refine_landmarks": True,
    "min_detection_confidence": 0.5,
    "min_tracking_confidence": 0.5,
    # Phone use (hand near ear)
    "phone_distance_threshold": 0.15,
    "phone_consec_frames": 30,      # ~1s at 30fps -> MEDIUM
    "phone_sustained_frames": 90,   # ~3s -> HIGH
    "max_num_hands": 2,
    "hands_model_complexity": 0,    # 0=Lite, 1=Full (Pi 5 should use 0)
    # Phone object (YOLO11n + NCNN) - opt-in via YOLO_ENABLED env var
    "yolo_enabled": False,
    "yolo_param_path": "",  # resolved by config.load_config()
    "yolo_bin_path": "",
    "yolo_confidence": 0.35,
    "yolo_iou": 0.45,
    "yolo_input_size": 416,
    "yolo_num_threads": 4,
    "yolo_stale_max_age_s": 0.5,
    "phone_object_iou_hand_threshold": 0.15,
    "phone_object_dist_ear_threshold": 0.30,
    "phone_object_consec_frames": 15,
    "phone_object_sustained_frames": 60,
}

_SEVERITY_ORDER = {None: 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}


@dataclass
class DetectionEvent:
    """A single drowsiness detection event.

    Field values match backend AlertType and Severity enums
    for direct MQTT serialization.
    """

    alert_type: str  # "EYE_CLOSURE", "YAWN", "HEAD_NOD", "PHONE_USE", "PHONE_OBJECT"
    severity: str  # "LOW", "MEDIUM", "HIGH"
    value: float  # measured value
    threshold: float  # threshold crossed
    timestamp: float = field(default_factory=time.monotonic)
    metadata: Optional[dict] = None


@dataclass
class FrameMetrics:
    """All metrics computed for a single frame."""

    ear: float = 0.0
    mar: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0
    perclos: float = 0.0
    face_detected: bool = False
    hand_ear_distance: float = math.inf
    hand_detected: bool = False
    closest_hand_xy: Optional[tuple] = None
    closest_ear_xy: Optional[tuple] = None
    phone_object_detected: bool = False
    phone_object_bbox: Optional[tuple] = None  # (x1, y1, x2, y2) normalized
    phone_object_conf: float = 0.0


class DetectionEngine:
    """Coordinates all drowsiness detection metrics.

    Designed to be usable headless (no OpenCV display required).
    Does NOT handle MQTT, SQLite, or actuator control.

    Usage:
        engine = DetectionEngine()
        events, metrics = engine.process(frame)
    """

    def __init__(self, config=None):
        self._config = {**DEFAULT_CONFIG, **(config or {})}
        cfg = self._config

        # MediaPipe FaceMesh
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=cfg["max_num_faces"],
            refine_landmarks=cfg["refine_landmarks"],
            min_detection_confidence=cfg["min_detection_confidence"],
            min_tracking_confidence=cfg["min_tracking_confidence"],
        )

        # PERCLOS tracker
        self._perclos = PerclosTracker(
            window_seconds=cfg["perclos_window_seconds"],
            ear_threshold=cfg["ear_threshold"],
        )

        # State: PERCLOS alert deduplication
        self._perclos_severity = None

        # State: Yawn detection
        self._mar_above_count = 0
        self._in_yawn = False

        # State: Head nod detection
        self._pitch_above_count = 0
        self._in_nod = False
        self._nod_alerted_high = False

        # MediaPipe Hands (separate model, runs alongside FaceMesh)
        self._hand_detector = HandDetector(
            max_num_hands=cfg["max_num_hands"],
            model_complexity=cfg["hands_model_complexity"],
            min_detection_confidence=cfg["min_detection_confidence"],
            min_tracking_confidence=cfg["min_tracking_confidence"],
        )

        # State: Phone use detection (HEAD_NOD-like: MEDIUM then HIGH)
        self._phone_close_count = 0
        self._in_phone_use = False
        self._phone_alerted_high = False

        # YOLO phone-object worker (None if disabled or ncnn unavailable)
        self._yolo = create_yolo_worker(self._config)
        if self._yolo is not None:
            self._yolo.start()

        # State: Phone object detection (YOLO + fusion)
        self._phone_object_count = 0
        self._in_phone_object = False
        self._phone_object_alerted_high = False

    def process(self, frame):
        """Process a single BGR frame.

        Args:
            frame: numpy array, BGR format (from cv2.VideoCapture).

        Returns:
            Tuple of (events: list[DetectionEvent], metrics: FrameMetrics).
        """
        events = []
        metrics = FrameMetrics()

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            metrics.face_detected = False
            return events, metrics

        landmarks = results.multi_face_landmarks[0].landmark
        metrics.face_detected = True

        # 1. EAR + PERCLOS
        left_ear = compute_ear(landmarks, LEFT_EYE)
        right_ear = compute_ear(landmarks, RIGHT_EYE)
        avg_ear = (left_ear + right_ear) / 2.0
        metrics.ear = avg_ear

        now = time.monotonic()
        self._perclos.update(avg_ear, timestamp=now)
        perclos_val = self._perclos.get_perclos()
        metrics.perclos = perclos_val

        events.extend(self._check_perclos(perclos_val, avg_ear))

        # 2. MAR
        mar = compute_mar(landmarks)
        metrics.mar = mar
        events.extend(self._check_yawn(mar))

        # 3. Head Pose
        pose = estimate_head_pose(landmarks, w, h)
        if pose is not None:
            pitch, yaw, roll = pose
            metrics.pitch = pitch
            metrics.yaw = yaw
            metrics.roll = roll
            events.extend(self._check_head_nod(pitch))

        # 4. Phone use (hand near ear). Requires face landmarks for ear pts.
        hand_results = self._hand_detector.process(rgb)
        distance, hand_detected, hand_xy, ear_xy = compute_min_hand_ear_distance(
            hand_results.multi_hand_landmarks, landmarks
        )
        metrics.hand_ear_distance = distance
        metrics.hand_detected = hand_detected
        metrics.closest_hand_xy = hand_xy
        metrics.closest_ear_xy = ear_xy
        events.extend(self._check_phone_use(distance))

        # 5. Phone object detection (YOLO, opt-in). Runs on a worker thread
        #    so heavy inference does not block the 30 FPS pipeline.
        if self._yolo is not None:
            self._yolo.submit(frame, now)
            bbox = self._yolo.get_latest()
            metrics.phone_object_detected = bbox is not None
            metrics.phone_object_bbox = (
                (bbox.x1, bbox.y1, bbox.x2, bbox.y2) if bbox else None
            )
            metrics.phone_object_conf = bbox.conf if bbox else 0.0
            left_ear_xy = (
                landmarks[LEFT_EAR_IDX].x,
                landmarks[LEFT_EAR_IDX].y,
            )
            right_ear_xy = (
                landmarks[RIGHT_EAR_IDX].x,
                landmarks[RIGHT_EAR_IDX].y,
            )
            events.extend(
                self._check_phone_object(
                    bbox,
                    hand_results.multi_hand_landmarks,
                    left_ear_xy,
                    right_ear_xy,
                )
            )

        return events, metrics

    def _check_perclos(self, perclos_val, ear):
        """Generate EYE_CLOSURE events on severity escalation."""
        events = []
        cfg = self._config

        if perclos_val >= cfg["perclos_high_threshold"]:
            current = "HIGH"
        elif perclos_val >= cfg["perclos_medium_threshold"]:
            current = "MEDIUM"
        elif perclos_val >= cfg["perclos_low_threshold"]:
            current = "LOW"
        else:
            current = None

        # Emit event only on escalation
        if _SEVERITY_ORDER.get(current, 0) > _SEVERITY_ORDER.get(
            self._perclos_severity, 0
        ):
            events.append(
                DetectionEvent(
                    alert_type="EYE_CLOSURE",
                    severity=current,
                    value=round(perclos_val, 3),
                    threshold=cfg[f"perclos_{current.lower()}_threshold"],
                    metadata={"ear": round(ear, 3)},
                )
            )

        self._perclos_severity = current
        return events

    def _check_yawn(self, mar):
        """Generate YAWN events. One per yawn occurrence."""
        events = []
        cfg = self._config

        if mar > cfg["mar_threshold"]:
            self._mar_above_count += 1
            if (
                self._mar_above_count >= cfg["yawn_consec_frames"]
                and not self._in_yawn
            ):
                self._in_yawn = True
                events.append(
                    DetectionEvent(
                        alert_type="YAWN",
                        severity="MEDIUM",
                        value=round(mar, 3),
                        threshold=cfg["mar_threshold"],
                    )
                )
        else:
            self._mar_above_count = 0
            self._in_yawn = False

        return events

    def _check_head_nod(self, pitch):
        """Generate HEAD_NOD events. MEDIUM on detection, HIGH on sustained.

        Euler pitch from cv2.RQDecomp3x3 wraps around ±180. Observed convention:
            Head upright:       pitch ≈ ±180 (at the wrap boundary)
            Head tilted up:     pitch positive, decreasing from 180 → 170 → 150 → ...
            Head tilted down:   pitch negative, increasing from -180 → -170 → -150 → ...

        A nod is detected when pitch is in [-pitch_threshold, 0), meaning the head
        has tilted forward enough that pitch moved away from the -180 wrap boundary
        toward 0. With pitch_threshold = 150, this triggers for pitch in [-150, 0).
        """
        events = []
        cfg = self._config

        if -cfg["pitch_threshold"] <= pitch < 0:
            self._pitch_above_count += 1

            if (
                self._pitch_above_count >= cfg["nod_consec_frames"]
                and not self._in_nod
            ):
                self._in_nod = True
                events.append(
                    DetectionEvent(
                        alert_type="HEAD_NOD",
                        severity="MEDIUM",
                        value=round(pitch, 1),
                        threshold=-cfg["pitch_threshold"],
                    )
                )

            if (
                self._pitch_above_count >= cfg["nod_sustained_frames"]
                and not self._nod_alerted_high
            ):
                self._nod_alerted_high = True
                events.append(
                    DetectionEvent(
                        alert_type="HEAD_NOD",
                        severity="HIGH",
                        value=round(pitch, 1),
                        threshold=-cfg["pitch_threshold"],
                    )
                )
        else:
            self._pitch_above_count = 0
            self._in_nod = False
            self._nod_alerted_high = False

        return events

    def _check_phone_use(self, distance):
        """Generate PHONE_USE events. MEDIUM on detection, HIGH on sustained.

        Fires when a hand landmark (wrist, thumb tip, index tip, or palm
        center) is within phone_distance_threshold of either ear tragion
        for phone_consec_frames consecutive frames. Escalates to HIGH
        when sustained for phone_sustained_frames (patron HEAD_NOD).
        """
        events = []
        cfg = self._config

        if distance < cfg["phone_distance_threshold"]:
            self._phone_close_count += 1

            if (
                self._phone_close_count >= cfg["phone_consec_frames"]
                and not self._in_phone_use
            ):
                self._in_phone_use = True
                events.append(
                    DetectionEvent(
                        alert_type="PHONE_USE",
                        severity="MEDIUM",
                        value=round(distance, 3),
                        threshold=cfg["phone_distance_threshold"],
                        metadata={"hand_ear_distance": round(distance, 3)},
                    )
                )

            if (
                self._phone_close_count >= cfg["phone_sustained_frames"]
                and not self._phone_alerted_high
            ):
                self._phone_alerted_high = True
                events.append(
                    DetectionEvent(
                        alert_type="PHONE_USE",
                        severity="HIGH",
                        value=round(distance, 3),
                        threshold=cfg["phone_distance_threshold"],
                        metadata={"hand_ear_distance": round(distance, 3)},
                    )
                )
        else:
            self._phone_close_count = 0
            self._in_phone_use = False
            self._phone_alerted_high = False

        return events

    def _check_phone_object(self, bbox, hand_landmarks_list, left_ear, right_ear):
        """Generate PHONE_OBJECT events using YOLO bbox fused with context.

        Fires when YOLO confidently detects a phone AND at least one of:
          - the phone bbox overlaps with a hand (IoU > threshold)
          - the phone is near either ear
          - the head is nodding (driver looking down at device)
        Escalates MEDIUM -> HIGH by consecutive frames, mirroring
        _check_phone_use.
        """
        events = []
        cfg = self._config

        if bbox is None or bbox.conf < cfg["yolo_confidence"]:
            self._phone_object_count = 0
            self._in_phone_object = False
            self._phone_object_alerted_high = False
            return events

        bbox_tuple = (bbox.x1, bbox.y1, bbox.x2, bbox.y2)
        iou_max = 0.0
        if hand_landmarks_list:
            for hand in hand_landmarks_list:
                hb = hand_bbox_from_landmarks(hand)
                iou_max = max(iou_max, iou(bbox_tuple, hb))

        center = bbox.center
        dist_ear = min(dist(center, left_ear), dist(center, right_ear))

        trigger = None
        if iou_max > cfg["phone_object_iou_hand_threshold"]:
            trigger = "iou_hand"
        elif dist_ear < cfg["phone_object_dist_ear_threshold"]:
            trigger = "near_ear"
        elif self._in_nod:
            trigger = "head_nod"

        if trigger is None:
            self._phone_object_count = 0
            self._in_phone_object = False
            self._phone_object_alerted_high = False
            return events

        self._phone_object_count += 1
        meta = {
            "conf": round(bbox.conf, 3),
            "iou_hand": round(iou_max, 3),
            "dist_ear": round(dist_ear, 3),
            "trigger": trigger,
        }

        if (
            self._phone_object_count >= cfg["phone_object_consec_frames"]
            and not self._in_phone_object
        ):
            self._in_phone_object = True
            events.append(
                DetectionEvent(
                    alert_type="PHONE_OBJECT",
                    severity="MEDIUM",
                    value=round(bbox.conf, 3),
                    threshold=cfg["yolo_confidence"],
                    metadata=meta,
                )
            )

        if (
            self._phone_object_count >= cfg["phone_object_sustained_frames"]
            and not self._phone_object_alerted_high
        ):
            self._phone_object_alerted_high = True
            events.append(
                DetectionEvent(
                    alert_type="PHONE_OBJECT",
                    severity="HIGH",
                    value=round(bbox.conf, 3),
                    threshold=cfg["yolo_confidence"],
                    metadata=meta,
                )
            )

        return events

    def reset(self):
        """Reset all internal state."""
        self._perclos.reset()
        self._perclos_severity = None
        self._mar_above_count = 0
        self._in_yawn = False
        self._pitch_above_count = 0
        self._in_nod = False
        self._nod_alerted_high = False
        self._phone_close_count = 0
        self._in_phone_use = False
        self._phone_alerted_high = False
        self._phone_object_count = 0
        self._in_phone_object = False
        self._phone_object_alerted_high = False

    def close(self):
        """Release MediaPipe resources."""
        if self._yolo is not None:
            self._yolo.stop()
        self._face_mesh.close()
        self._hand_detector.close()
