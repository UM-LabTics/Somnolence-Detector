import numpy as np

# MediaPipe Face Mesh inner lip landmark indices for MAR
# Reference: https://github.com/google/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model_uv_visualization.png
#
# Each lip contour has 8 points:
#   P1 (left corner), P2 (upper-left), P3 (upper-center), P4 (upper-right),
#   P5 (right corner), P6 (lower-right), P7 (lower-center), P8 (lower-left)
#
# MAR = (||P2-P8|| + ||P3-P7|| + ||P4-P6||) / (2 * ||P1-P5||)

INNER_LIP = [78, 82, 13, 312, 308, 317, 14, 87]


def compute_mar(landmarks, lip_indices=INNER_LIP):
    """Compute Mouth Aspect Ratio for yawn detection.

    Args:
        landmarks: MediaPipe face mesh landmarks (478 points).
        lip_indices: List of 8 landmark indices [P1..P8].

    Returns:
        Float MAR value. ~0.1-0.2 when closed, ~0.6+ when yawning.
    """
    pts = np.array([(landmarks[i].x, landmarks[i].y) for i in lip_indices])

    # Vertical distances (3 pairs for robustness)
    v1 = np.linalg.norm(pts[1] - pts[7])  # P2-P8
    v2 = np.linalg.norm(pts[2] - pts[6])  # P3-P7
    v3 = np.linalg.norm(pts[3] - pts[5])  # P4-P6

    # Horizontal distance
    h = np.linalg.norm(pts[0] - pts[4])  # P1-P5

    if h == 0:
        return 0.0

    mar = (v1 + v2 + v3) / (2.0 * h)
    return mar
