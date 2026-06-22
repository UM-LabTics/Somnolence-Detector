"""Centralized configuration for the Somnolence Detector."""

import os
import uuid
from pathlib import Path

_DEVICE_ID_FILE = Path(__file__).parent / ".device_id"

# Detection defaults (same values as engine.DEFAULT_CONFIG)
_DETECTION_DEFAULTS = {
    "ear_threshold": 0.21,
    "eye_closure_low_s": 2.0,
    "eye_closure_medium_s": 5.0,
    "eye_closure_high_s": 10.0,
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

    # MQTT client identity (AWS IoT Core requires it to match the Thing).
    # Empty/unset -> paho generates a random id (fine for local Mosquitto).
    config["mqtt_client_id"] = os.environ.get("MQTT_CLIENT_ID") or None

    # MQTT TLS (mutual auth). Same env var names as the backend client.
    # Set all three to publish to IoT Core over 8883; unset -> plain local mode.
    config["mqtt_ca_cert"] = os.environ.get("MQTT_CA_CERT") or None
    config["mqtt_client_cert"] = os.environ.get("MQTT_CLIENT_CERT") or None
    config["mqtt_client_key"] = os.environ.get("MQTT_CLIENT_KEY") or None

    # ALPN protocol for MQTT over 443 (set to "x-amzn-mqtt-ca" for AWS IoT
    # Core on networks that block port 8883). Unset -> standard 8883 path.
    config["mqtt_alpn"] = os.environ.get("MQTT_ALPN") or None

    # Sync
    config["retry_interval"] = 5.0
    config["heartbeat_interval"] = 30.0
    config["batch_size"] = 50
    config["db_path"] = str(Path(__file__).parent / "somnolence_local.db")

    # Camera. On a Raspberry Pi 5 the libcamera/ISP pipeline exposes many
    # /dev/videoN nodes besides the USB webcam, so index 0 is often wrong.
    # Use `v4l2-ctl --list-devices` to find the webcam's real index.
    config["camera_index"] = int(os.environ.get("CAMERA_INDEX", "0"))

    # Sensors & Actuators
    config["environmental_interval"] = 30.0
    config["mock_sensors"] = os.environ.get("MOCK_SENSORS", "true").lower() == "true"
    config["mock_actuators"] = os.environ.get("MOCK_ACTUATORS", "true").lower() == "true"

    # Hardware pins (BCM numbering)
    config["buzzer_pin"] = int(os.environ.get("BUZZER_PIN", "18"))
    config["led_pin"] = int(os.environ.get("LED_PIN", "23"))

    # Peripheral UART ports
    config["gps_port"] = os.environ.get("GPS_PORT", "/dev/ttyAMA0")
    config["co2_port"] = os.environ.get("CO2_PORT", "/dev/ttyAMA1")

    # Minimum vehicle speed (km/h) required to trigger actuators and publish MQTT alerts.
    # 0 = always alert regardless of speed (default).
    # Example: 5 suppresses alerts when the vehicle is parked or barely moving.
    # TODO(frontend): expose this as a per-device slider in the dashboard
    #   so operators can adjust the threshold without redeploying.
    config["alert_min_speed_kmh"] = float(os.environ.get("ALERT_MIN_SPEED_KMH", "0"))

    return config
