import numpy as np

# MediaPipe Face Mesh landmark indices for eyes
# Reference: https://github.com/google/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model_uv_visualization.png
#
# Each eye has 6 points:
#   P1 (outer corner), P2 (upper-outer), P3 (upper-inner),
#   P4 (inner corner), P5 (lower-inner), P6 (lower-outer)
#
# EAR = (||P2-P6|| + ||P3-P5||) / (2 * ||P1-P4||)
# From: Soukupova & Cech, "Real-Time Eye Blink Detection using Facial Landmarks", 2016

RIGHT_EYE = [33, 160, 158, 133, 153, 144]
LEFT_EYE = [362, 385, 387, 263, 373, 380]


def compute_ear(landmarks, eye_indices):
    """Compute Eye Aspect Ratio for one eye.

    Args:
        landmarks: MediaPipe face mesh landmarks (478 points).
        eye_indices: List of 6 landmark indices [P1, P2, P3, P4, P5, P6].

    Returns:
        Float EAR value. ~0.25-0.30 when open, <0.20 when closed.
    """
    pts = np.array([(landmarks[i].x, landmarks[i].y) for i in eye_indices])

    # Vertical distances
    v1 = np.linalg.norm(pts[1] - pts[5])  # P2-P6
    v2 = np.linalg.norm(pts[2] - pts[4])  # P3-P5

    # Horizontal distance
    h = np.linalg.norm(pts[0] - pts[3])   # P1-P4

    if h == 0:
        return 0.0

    ear = (v1 + v2) / (2.0 * h)
    return ear
