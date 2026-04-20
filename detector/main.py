import logging
import signal
import sys
import time

import cv2

from actuators import create_actuator
from config import get_or_create_device_id, load_config
from engine import DetectionEngine, FrameMetrics
from sensors import create_sensor
from sync import SyncManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Alert display labels
ALERT_LABELS = {
    "EYE_CLOSURE": "SOMNOLENCIA",
    "YAWN": "BOSTEZO",
    "HEAD_NOD": "CABECEO",
    "PHONE_USE": "USO DE CELULAR",
}

SEVERITY_COLORS = {
    "LOW": (0, 255, 255),  # Yellow
    "MEDIUM": (0, 165, 255),  # Orange
    "HIGH": (0, 0, 255),  # Red
}

ALERT_DISPLAY_SECONDS = 3.0


def draw_metrics(frame, metrics, config):
    """Draw all detection metrics on the frame."""
    if not metrics.face_detected:
        cv2.putText(
            frame,
            "No face detected",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 165, 255),
            2,
        )
        return

    # Line 1: EAR, MAR, PERCLOS
    ear_color = (
        (0, 255, 0) if metrics.ear >= config["ear_threshold"] else (0, 0, 255)
    )
    mar_color = (
        (0, 255, 0) if metrics.mar < config["mar_threshold"] else (0, 165, 255)
    )

    perclos_pct = metrics.perclos * 100
    if metrics.perclos >= config["perclos_high_threshold"]:
        perclos_color = (0, 0, 255)
    elif metrics.perclos >= config["perclos_medium_threshold"]:
        perclos_color = (0, 165, 255)
    elif metrics.perclos >= config["perclos_low_threshold"]:
        perclos_color = (0, 255, 255)
    else:
        perclos_color = (0, 255, 0)

    y = 30
    cv2.putText(
        frame, f"EAR: {metrics.ear:.3f}", (10, y),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, ear_color, 2,
    )
    cv2.putText(
        frame, f"MAR: {metrics.mar:.3f}", (180, y),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, mar_color, 2,
    )
    cv2.putText(
        frame, f"PERCLOS: {perclos_pct:.1f}%", (350, y),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, perclos_color, 2,
    )

    # Line 2: Head pose
    y = 60
    pitch_color = (
        (0, 0, 255)
        if -config["pitch_threshold"] <= metrics.pitch < 0
        else (0, 255, 0)
    )
    cv2.putText(
        frame,
        f"P:{metrics.pitch:.1f} Y:{metrics.yaw:.1f} R:{metrics.roll:.1f}",
        (10, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        pitch_color,
        2,
    )

    # Line 3: Hand-Ear distance + YOLO phone indicator
    y = 90
    phone_indicator = " [PHONE]" if metrics.phone_object_detected else ""
    if metrics.hand_detected:
        dist_color = (
            (0, 0, 255)
            if metrics.hand_ear_distance < config["phone_distance_threshold"]
            else (0, 255, 0)
        )
        cv2.putText(
            frame,
            f"Hand-Ear: {metrics.hand_ear_distance:.3f}{phone_indicator}",
            (10, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            dist_color,
            2,
        )

        # Line from closest hand point to closest ear landmark
        if metrics.closest_hand_xy is not None and metrics.closest_ear_xy is not None:
            h, w = frame.shape[:2]
            hp = (
                int(metrics.closest_hand_xy[0] * w),
                int(metrics.closest_hand_xy[1] * h),
            )
            ep = (
                int(metrics.closest_ear_xy[0] * w),
                int(metrics.closest_ear_xy[1] * h),
            )
            cv2.line(frame, hp, ep, dist_color, 2)
            cv2.circle(frame, hp, 5, dist_color, -1)
            cv2.circle(frame, ep, 5, dist_color, -1)
    else:
        cv2.putText(
            frame,
            f"Hand-Ear: -{phone_indicator}",
            (10, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (128, 128, 128),
            2,
        )


def draw_alerts(frame, active_alerts):
    """Draw active alert banners at the bottom of the frame."""
    h = frame.shape[0]
    y = h - 20

    for event, _ in reversed(active_alerts):
        label = ALERT_LABELS.get(event.alert_type, event.alert_type)
        color = SEVERITY_COLORS.get(event.severity, (0, 0, 255))
        text = f"ALERTA: {label} ({event.severity})"
        cv2.putText(
            frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 3
        )
        y -= 35


def main():
    config = load_config()
    device_id = get_or_create_device_id()
    logger.info(f"Device ID: {device_id}")

    engine = DetectionEngine(config)
    sync_manager = SyncManager(device_id, config)
    sensor = create_sensor(config)
    actuator = create_actuator(config)

    # Graceful shutdown
    shutdown_requested = False

    def signal_handler(signum, frame):
        nonlocal shutdown_requested
        shutdown_requested = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    sync_manager.start()

    backend = cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_V4L2
    cap = cv2.VideoCapture(0, backend)
    active_alerts = []
    last_env_time = 0.0

    logger.info("Somnolence Detector started — press 'q' to quit")

    while cap.isOpened() and not shutdown_requested:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        events, metrics = engine.process(frame)

        now_mono = time.monotonic()
        for event in events:
            sync_manager.queue_alert(event)
            actuator.activate(event.severity)
            active_alerts.append((event, now_mono + ALERT_DISPLAY_SECONDS))
            label = ALERT_LABELS.get(event.alert_type, event.alert_type)
            logger.info(
                f"[ALERT] {label} severity={event.severity} "
                f"value={event.value} threshold={event.threshold}"
            )

        # Environmental readings at configured interval
        now_wall = time.time()
        env_interval = config.get("environmental_interval", 30.0)
        if now_wall - last_env_time >= env_interval:
            reading = sensor.read()
            if reading:
                sync_manager.queue_environmental(reading)
            last_env_time = now_wall

        # Purge expired display alerts
        active_alerts = [(e, t) for e, t in active_alerts if t > now_mono]

        draw_metrics(frame, metrics, config)
        draw_alerts(frame, active_alerts)

        cv2.imshow("Somnolence Detector", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # Cleanup
    logger.info("Shutting down...")
    actuator.deactivate()
    actuator.close()
    sensor.close()
    sync_manager.stop()
    engine.close()
    cap.release()
    cv2.destroyAllWindows()
    logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
