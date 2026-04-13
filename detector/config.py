"""Centralized configuration for the Somnolence Detector."""

import os
import uuid
from pathlib import Path

_DEVICE_ID_FILE = Path(__file__).parent / ".device_id"

# Detection defaults (same values as engine.DEFAULT_CONFIG)
_DETECTION_DEFAULTS = {
    "ear_threshold": 0.21,
    "perclos_window_seconds": 60.0,
    "perclos_low_threshold": 0.15,
    "perclos_medium_threshold": 0.25,
    "perclos_high_threshold": 0.40,
    "mar_threshold": 0.55,
    "yawn_consec_frames": 30,
    "pitch_threshold": 150.0,
    "nod_consec_frames": 25,
    "nod_sustained_frames": 75,
    "max_num_faces": 1,
    "refine_landmarks": True,
    "min_detection_confidence": 0.5,
    "min_tracking_confidence": 0.5,
    # Phone use (hand near ear)
    "phone_distance_threshold": 0.15,
    "phone_consec_frames": 30,
    "phone_sustained_frames": 90,
    "max_num_hands": 2,
    "hands_model_complexity": 0,
    # Phone object (YOLO11n + NCNN) - opt-in via YOLO_ENABLED env var
    "yolo_enabled": False,
    "yolo_param_path": str(
        Path(__file__).parent / "models" / "yolo11n_416.ncnn.param"
    ),
    "yolo_bin_path": str(
        Path(__file__).parent / "models" / "yolo11n_416.ncnn.bin"
    ),
    "yolo_confidence": 0.55,              # strict threshold for COCO-generic on webcam
    "yolo_iou": 0.45,
    "yolo_input_size": 320,               # Pi 5 CPU budget; ~40% less compute than 416
    "yolo_num_threads": 2,                # leaves 2 cores for MediaPipe
    "yolo_stale_max_age_s": 0.5,
    "yolo_min_box_area": 0.008,           # reject tiny boxes (< 0.8% of frame)
    "yolo_max_box_area": 0.35,            # reject absurdly large boxes (> 35%)
    "yolo_min_aspect_ratio": 0.3,         # phones are tall (~0.45) or wide (~2.2)
    "yolo_max_aspect_ratio": 3.5,         # reject square-ish false positives
    "phone_object_iou_hand_threshold": 0.15,
    "phone_object_dist_ear_threshold": 0.30,
    "phone_object_consec_frames": 10,     # ~1.5s sustained pose
    "phone_object_sustained_frames": 45,  # ~6s sustained -> HIGH
}


def get_or_create_device_id() -> str:
    """Return a stable UUID device identifier.

    Resolution order:
    1. DEVICE_ID environment variable
    2. Contents of detector/.device_id file
    3. Generate new UUID, save to detector/.device_id, return it
    """
    env_id = os.environ.get("DEVICE_ID")
    if env_id:
        uuid.UUID(env_id)  # validate
        return env_id

    if _DEVICE_ID_FILE.exists():
        content = _DEVICE_ID_FILE.read_text().strip()
        if content:
            uuid.UUID(content)  # validate
            return content

    new_id = str(uuid.uuid4())
    _DEVICE_ID_FILE.write_text(new_id + "\n")
    return new_id


def load_config() -> dict:
    """Build the full configuration dictionary."""
    config = {**_DETECTION_DEFAULTS}

    # MQTT
    config["mqtt_broker"] = os.environ.get("MQTT_BROKER", "localhost")
    config["mqtt_port"] = int(os.environ.get("MQTT_PORT", "1883"))
    config["mqtt_prefix"] = os.environ.get("MQTT_TOPIC_PREFIX", "somnolence")

    # Sync
    config["retry_interval"] = 5.0
    config["heartbeat_interval"] = 30.0
    config["batch_size"] = 50
    config["db_path"] = str(Path(__file__).parent / "somnolence_local.db")

    # Sensors & Actuators
    config["environmental_interval"] = 30.0
    config["mock_sensors"] = os.environ.get("MOCK_SENSORS", "true").lower() == "true"
    config["mock_actuators"] = os.environ.get("MOCK_ACTUATORS", "true").lower() == "true"

    # YOLO object detection (opt-in, requires ncnn + model files)
    config["yolo_enabled"] = (
        os.environ.get("YOLO_ENABLED", "false").lower() == "true"
    )

    return config
