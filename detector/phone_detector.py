"""Phone usage detection via MediaPipe Hands + hand-to-ear distance.

The driver's hand held near the ear is the classic phone-call gesture.
This module wraps MediaPipe Hands and provides a pure function that
computes the minimum Euclidean distance (normalized [0,1] space) between
any of a set of representative hand landmarks and either ear tragion
landmark from MediaPipe FaceMesh.
"""

import math
from typing import Optional

import mediapipe as mp
import numpy as np

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
