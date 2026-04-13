"""Geometric helpers shared by detectors.

All coordinates are expected to be in normalized [0, 1] space (as
produced by MediaPipe landmarks and the YOLO post-processor).
"""

import math


def iou(a: tuple, b: tuple) -> float:
    """Intersection-over-union of two axis-aligned bboxes (x1, y1, x2, y2)."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    iw = ix2 - ix1
    ih = iy2 - iy1
    if iw <= 0.0 or ih <= 0.0:
        return 0.0

    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    if union <= 0.0:
        return 0.0
    return inter / union


def dist(p: tuple, q: tuple) -> float:
    """Euclidean distance between two 2D points."""
    return math.hypot(p[0] - q[0], p[1] - q[1])
