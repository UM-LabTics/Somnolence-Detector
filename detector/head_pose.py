import numpy as np
import cv2

# MediaPipe Face Mesh landmark indices for head pose estimation
# These 6 points are anatomically stable and well-distributed across the face.
FACE_2D_INDICES = [1, 199, 33, 263, 61, 291]

# 3D model points (Ahlberg generic face model, centered at nose tip)
MODEL_POINTS = np.array(
    [
        (0.0, 0.0, 0.0),  # Nose tip
        (0.0, -63.6, -12.5),  # Chin
        (-43.3, 32.7, -26.0),  # Left eye outer corner
        (43.3, 32.7, -26.0),  # Right eye outer corner
        (-28.9, -28.9, -24.1),  # Left mouth corner
        (28.9, -28.9, -24.1),  # Right mouth corner
    ],
    dtype=np.float64,
)


def get_camera_matrix(frame_width, frame_height):
    """Construct approximate camera intrinsic matrix.

    Assumes focal length ~ frame width (typical webcam).
    Principal point at frame center. No lens distortion.

    Args:
        frame_width: Frame width in pixels.
        frame_height: Frame height in pixels.

    Returns:
        Tuple of (camera_matrix, dist_coeffs).
    """
    focal_length = float(frame_width)
    center = (frame_width / 2.0, frame_height / 2.0)

    camera_matrix = np.array(
        [
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1],
        ],
        dtype=np.float64,
    )

    dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    return camera_matrix, dist_coeffs


def estimate_head_pose(landmarks, frame_width, frame_height):
    """Estimate head orientation from facial landmarks using PnP solving.

    Args:
        landmarks: MediaPipe face mesh landmarks (478 points).
        frame_width: Frame width in pixels.
        frame_height: Frame height in pixels.

    Returns:
        Tuple of (pitch, yaw, roll) in degrees, or None if PnP fails.
        Pitch: negative = looking down / head nodding forward.
        Yaw: positive = looking right.
        Roll: positive = tilting right.
    """
    # Extract 2D image points from landmarks
    image_points = np.array(
        [
            (landmarks[i].x * frame_width, landmarks[i].y * frame_height)
            for i in FACE_2D_INDICES
        ],
        dtype=np.float64,
    )

    camera_matrix, dist_coeffs = get_camera_matrix(frame_width, frame_height)

    success, rvec, tvec = cv2.solvePnP(
        MODEL_POINTS,
        image_points,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )

    if not success:
        return None

    # Convert rotation vector to rotation matrix
    rmat, _ = cv2.Rodrigues(rvec)

    # Extract Euler angles from rotation matrix
    angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)

    pitch = angles[0]
    yaw = angles[1]
    roll = angles[2]

    return pitch, yaw, roll
