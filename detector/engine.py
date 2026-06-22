import math
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

from ear import LEFT_EYE, RIGHT_EYE, compute_ear
from head_pose import estimate_head_pose
from mar import compute_mar
from phone_detector import HandDetector, compute_min_hand_ear_distance

# Default configuration
DEFAULT_CONFIG = {
    # EAR / Eye closure duration (seconds of continuous closure)
    "ear_threshold": 0.21,
    "eye_closure_low_s": 2.0,
    "eye_closure_medium_s": 5.0,
    "eye_closure_high_s": 10.0,
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
}

_SEVERITY_ORDER = {None: 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}


@dataclass
class DetectionEvent:
    """A single drowsiness detection event.

    Field values match backend AlertType and Severity enums
    for direct MQTT serialization.
    """

    alert_type: str  # "EYE_CLOSURE", "YAWN", "HEAD_NOD"
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
    eye_closure_s: float = 0.0   # seconds eyes have been continuously closed
    face_detected: bool = False
    hand_ear_distance: float = math.inf
    hand_detected: bool = False
    closest_hand_xy: Optional[tuple] = None
    closest_ear_xy: Optional[tuple] = None


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

        # State: eye closure duration tracking
        self._eye_closed_since: Optional[float] = None   # monotonic time eyes closed
        self._eye_closure_severity: Optional[str] = None  # highest severity alerted this instance

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

        # 1. EAR + eye closure duration
        left_ear = compute_ear(landmarks, LEFT_EYE)
        right_ear = compute_ear(landmarks, RIGHT_EYE)
        avg_ear = (left_ear + right_ear) / 2.0
        metrics.ear = avg_ear

        now = time.monotonic()
        events.extend(self._check_eye_closure(avg_ear, now))
        if self._eye_closed_since is not None:
            metrics.eye_closure_s = now - self._eye_closed_since

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

        return events, metrics

    def _check_eye_closure(self, ear, now):
        """Generate EYE_CLOSURE events based on continuous closure duration.

        Escalates LOW → MEDIUM → HIGH within the same closure instance.
        Resets when eyes open (EAR >= threshold).
        """
        events = []
        cfg = self._config

        if ear < cfg["ear_threshold"]:
            # Eyes closed — start timer if not already running
            if self._eye_closed_since is None:
                self._eye_closed_since = now
                self._eye_closure_severity = None

            elapsed = now - self._eye_closed_since

            if elapsed >= cfg["eye_closure_high_s"] and self._eye_closure_severity != "HIGH":
                self._eye_closure_severity = "HIGH"
                events.append(DetectionEvent(
                    alert_type="EYE_CLOSURE", severity="HIGH",
                    value=round(elapsed, 2), threshold=cfg["eye_closure_high_s"],
                    metadata={"ear": round(ear, 3)},
                ))
            elif elapsed >= cfg["eye_closure_medium_s"] and self._eye_closure_severity not in ("MEDIUM", "HIGH"):
                self._eye_closure_severity = "MEDIUM"
                events.append(DetectionEvent(
                    alert_type="EYE_CLOSURE", severity="MEDIUM",
                    value=round(elapsed, 2), threshold=cfg["eye_closure_medium_s"],
                    metadata={"ear": round(ear, 3)},
                ))
            elif elapsed >= cfg["eye_closure_low_s"] and self._eye_closure_severity is None:
                self._eye_closure_severity = "LOW"
                events.append(DetectionEvent(
                    alert_type="EYE_CLOSURE", severity="LOW",
                    value=round(elapsed, 2), threshold=cfg["eye_closure_low_s"],
                    metadata={"ear": round(ear, 3)},
                ))
        else:
            # Eyes open — reset instance
            self._eye_closed_since = None
            self._eye_closure_severity = None

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

    def reset(self):
        """Reset all internal state."""
        self._eye_closed_since = None
        self._eye_closure_severity = None
        self._mar_above_count = 0
        self._in_yawn = False
        self._pitch_above_count = 0
        self._in_nod = False
        self._nod_alerted_high = False
        self._phone_close_count = 0
        self._in_phone_use = False
        self._phone_alerted_high = False

    def close(self):
        """Release MediaPipe resources."""
        self._face_mesh.close()
        self._hand_detector.close()
