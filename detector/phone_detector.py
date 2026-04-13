"""Phone usage detection via MediaPipe Hands + hand-to-ear distance + YOLO object detection.

Two-condition strategy:
  1. Hand near ear  — MediaPipe Hands landmark distance to ear tragion.
  2. Phone visible  — YOLOv8n detects COCO class 67 ("cell phone") in the frame.

Both conditions must be true for a PHONE_USE alert to fire.
If ultralytics is not installed or the model cannot load, condition 2 is
skipped and the detector falls back to hand-only behaviour.
"""

import logging
import math
from typing import Optional

import mediapipe as mp
import numpy as np

logger = logging.getLogger(__name__)

# MediaPipe FaceMesh indices for ear tragion (front of the ear, where
# a phone earpiece touches the head).
LEFT_EAR_IDX = 234
RIGHT_EAR_IDX = 454

# MediaPipe Hands landmark indices used for the distance check.
# 0 = WRIST (stable anchor point)
# 4 = THUMB_TIP (closest to ear when holding phone)
# 8 = INDEX_FINGER_TIP
# 9 = MIDDLE_FINGER_MCP (proxy for palm center)
HAND_POINTS = (0, 4, 8, 9)


class HandDetector:
    """Wraps mp.solutions.hands.Hands for video-stream hand tracking.

    Lifecycle mirrors DetectionEngine's face_mesh member: instantiate
    once, call process() per frame, close() on shutdown.
    """

    def __init__(
        self,
        max_num_hands: int = 2,
        model_complexity: int = 0,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ):
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

        # Warm up the TFLite model to avoid a 500-1000ms hitch on the
        # first real frame.
        warmup = np.zeros((480, 640, 3), dtype=np.uint8)
        self._hands.process(warmup)

    def process(self, rgb_frame):
        """Run hand detection on an RGB frame. Returns mediapipe result."""
        return self._hands.process(rgb_frame)

    def close(self):
        self._hands.close()


class PhoneObjectDetector:
    """Detects 'cell phone' objects in a frame using YOLOv8n.

    Runs inference every `skip_frames` frames and caches the last result
    to keep CPU usage low on embedded hardware.

    If ultralytics is unavailable, `available` is False and `detect()`
    always returns True so the hand-distance check is the sole gate.
    """

    PHONE_CLASS_ID = 67  # COCO class index for "cell phone"

    def __init__(self, confidence: float = 0.4, skip_frames: int = 3):
        self._confidence = confidence
        self._skip_frames = max(1, skip_frames)
        self._frame_count = 0
        self._last_result = False
        self._model = None
        self.available = False

        try:
            from ultralytics import YOLO  # noqa: PLC0415
            self._model = YOLO("yolov8n.pt")
            # Suppress ultralytics verbose output after first load
            self._model.overrides["verbose"] = False
            self.available = True
            logger.info("PhoneObjectDetector: YOLOv8n loaded (COCO class 67)")
        except Exception as exc:
            logger.warning(
                "PhoneObjectDetector: ultralytics unavailable — "
                "falling back to hand-only detection. (%s)", exc
            )

    def detect(self, bgr_frame) -> bool:
        """Return True if a cell phone is visible in the frame.

        Always returns True when YOLO is unavailable (passthrough).
        """
        if not self.available:
            return True

        self._frame_count += 1
        if self._frame_count % self._skip_frames != 0:
            return self._last_result

        results = self._model(
            bgr_frame,
            classes=[self.PHONE_CLASS_ID],
            conf=self._confidence,
            verbose=False,
        )
        self._last_result = any(len(r.boxes) > 0 for r in results)
        return self._last_result

    def close(self) -> None:
        self._model = None


def compute_min_hand_ear_distance(
    hand_landmarks_list,
    face_landmarks,
) -> tuple[float, bool, Optional[tuple], Optional[tuple]]:
    """Compute minimum hand-to-ear distance in normalized [0,1] space.

    Args:
        hand_landmarks_list: `multi_hand_landmarks` from HandDetector.process(),
            or None/empty if no hands detected.
        face_landmarks: MediaPipe FaceMesh landmark list (478 or 468 points).

    Returns:
        Tuple of:
            - min_distance (float): minimum distance found, or math.inf
              if no hands detected.
            - hand_detected (bool): True if any hand was detected.
            - closest_hand_xy (tuple|None): (x, y) of the closest hand
              point in normalized space, for visualization.
            - closest_ear_xy (tuple|None): (x, y) of the closest ear
              landmark, for visualization.
    """
    if not hand_landmarks_list:
        return math.inf, False, None, None

    left_ear = (face_landmarks[LEFT_EAR_IDX].x, face_landmarks[LEFT_EAR_IDX].y)
    right_ear = (face_landmarks[RIGHT_EAR_IDX].x, face_landmarks[RIGHT_EAR_IDX].y)
    ears = (left_ear, right_ear)

    min_d = math.inf
    closest_hand = None
    closest_ear = None

    for hand in hand_landmarks_list:
        for idx in HAND_POINTS:
            hp = (hand.landmark[idx].x, hand.landmark[idx].y)
            for ep in ears:
                d = math.hypot(hp[0] - ep[0], hp[1] - ep[1])
                if d < min_d:
                    min_d = d
                    closest_hand = hp
                    closest_ear = ep

    return min_d, True, closest_hand, closest_ear
