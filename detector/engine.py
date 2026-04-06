import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

from ear import LEFT_EYE, RIGHT_EYE, compute_ear
from head_pose import estimate_head_pose
from mar import compute_mar
from perclos import PerclosTracker

# Default configuration
DEFAULT_CONFIG = {
    # EAR / PERCLOS
    "ear_threshold": 0.21,
    "perclos_window_seconds": 60.0,
    "perclos_low_threshold": 0.60,
    "perclos_medium_threshold": 0.70,
    "perclos_high_threshold": 0.80,
    # MAR / Yawn
    "mar_threshold": 0.55,
    "yawn_consec_frames": 30,  # ~1s at 30fps
    # Head pose / Nod
    "pitch_threshold": 15.0,  # degrees
    "nod_consec_frames": 25,  # ~0.8s at 30fps
    "nod_sustained_frames": 75,  # ~2.5s for HIGH
    # MediaPipe
    "max_num_faces": 1,
    "refine_landmarks": True,
    "min_detection_confidence": 0.5,
    "min_tracking_confidence": 0.5,
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
    perclos: float = 0.0
    face_detected: bool = False


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
        """Generate HEAD_NOD events. MEDIUM on detection, HIGH on sustained."""
        events = []
        cfg = self._config

        # Negative pitch = head tilting forward (nodding)
        if pitch < -cfg["pitch_threshold"]:
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
                        value=round(abs(pitch), 1),
                        threshold=cfg["pitch_threshold"],
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
                        value=round(abs(pitch), 1),
                        threshold=cfg["pitch_threshold"],
                    )
                )
        else:
            self._pitch_above_count = 0
            self._in_nod = False
            self._nod_alerted_high = False

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

    def close(self):
        """Release MediaPipe resources."""
        self._face_mesh.close()
