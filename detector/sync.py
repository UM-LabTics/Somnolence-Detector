"""Store-and-forward sync manager for offline-first operation."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from local_db import LocalDB
from mqtt_publisher import MQTTPublisher

if TYPE_CHECKING:
    from engine import DetectionEvent

logger = logging.getLogger(__name__)


class SyncManager:
    """Orchestrates local persistence and MQTT publishing.

    Data flow:
    1. queue_alert/queue_environmental saves to SQLite (synced=False)
    2. If MQTT connected, attempts immediate publish
    3. If publish succeeds, marks synced=True
    4. Background thread retries pending records periodically
    5. Background thread sends heartbeat at configured interval
    """

    def __init__(self, device_id: str, config: dict):
        self._device_id = device_id
        self._retry_interval = config.get("retry_interval", 5.0)
        self._heartbeat_interval = config.get("heartbeat_interval", 30.0)
        self._batch_size = config.get("batch_size", 50)

        self._db = LocalDB(config.get("db_path", "somnolence_local.db"))
        self._mqtt = MQTTPublisher(
            broker=config.get("mqtt_broker", "localhost"),
            port=config.get("mqtt_port", 1883),
            device_id=device_id,
            prefix=config.get("mqtt_prefix", "somnolence"),
            client_id=config.get("mqtt_client_id"),
            ca_cert=config.get("mqtt_ca_cert"),
            client_cert=config.get("mqtt_client_cert"),
            client_key=config.get("mqtt_client_key"),
            alpn=config.get("mqtt_alpn"),
        )

        self._stop_event = threading.Event()
        self._thread = None

    def start(self) -> None:
        """Connect MQTT and start the background retry/heartbeat thread."""
        self._mqtt.connect()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._background_loop, daemon=True, name="sync-retry"
        )
        self._thread.start()
        logger.info(f"SyncManager started for device {self._device_id[:8]}...")

    def stop(self) -> None:
        """Stop background thread, disconnect MQTT, close SQLite."""
        logger.info("SyncManager stopping...")
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        self._mqtt.disconnect()
        pending = self._db.pending_count()
        logger.info(
            f"SyncManager stopped. Pending: "
            f"{pending['alerts']} alerts, {pending['environmental']} environmental"
        )
        self._db.close()

    def queue_alert(self, event: DetectionEvent) -> None:
        """Persist a DetectionEvent and attempt immediate MQTT publish."""
        timestamp = datetime.now(timezone.utc).isoformat()

        row_id = self._db.save_alert(
            alert_type=event.alert_type,
            severity=event.severity,
            value=event.value,
            threshold=event.threshold,
            metadata=event.metadata,
            timestamp=timestamp,
        )

        payload = {
            "alert_type": event.alert_type,
            "severity": event.severity,
            "value": event.value,
            "threshold": event.threshold,
        }
        if event.metadata:
            payload["metadata"] = event.metadata

        if self._mqtt.is_connected:
            if self._mqtt.publish_alert(payload):
                self._db.mark_alert_synced(row_id)

    def queue_environmental(self, reading: dict) -> None:
        """Persist an environmental reading and attempt immediate publish."""
        timestamp = datetime.now(timezone.utc).isoformat()

        row_id = self._db.save_environmental(
            temperature=reading.get("temperature"),
            humidity=reading.get("humidity"),
            co2=reading.get("co2"),
            gps_lat=reading.get("gps_lat"),
            gps_lon=reading.get("gps_lon"),
            gps_speed_kmh=reading.get("gps_speed_kmh"),
            gps_moving=reading.get("gps_moving"),
            gps_fix=reading.get("gps_fix"),
            timestamp=timestamp,
        )

        payload: dict = {"timestamp": timestamp}
        for k in ("temperature", "humidity", "co2"):
            if reading.get(k) is not None:
                payload[k] = reading[k]
        for k in ("gps_lat", "gps_lon", "gps_speed_kmh", "gps_moving", "gps_fix", "gps_utc"):
            if reading.get(k) is not None:
                payload[k] = reading[k]

        if self._mqtt.is_connected:
            if self._mqtt.publish_environmental(payload):
                self._db.mark_environmental_synced(row_id)

    def _background_loop(self) -> None:
        """Retry pending + heartbeat loop."""
        last_heartbeat = 0.0

        while not self._stop_event.is_set():
            now = time.monotonic()

            if self._mqtt.is_connected:
                self._retry_pending()

            if now - last_heartbeat >= self._heartbeat_interval:
                self._send_heartbeat()
                last_heartbeat = now

            self._stop_event.wait(timeout=self._retry_interval)

    def _retry_pending(self) -> None:
        """Fetch and publish pending records from SQLite."""
        if not self._mqtt.is_connected:
            return

        # Alerts
        pending_alerts = self._db.get_pending_alerts(limit=self._batch_size)
        alert_synced = 0
        for alert in pending_alerts:
            payload = {
                "alert_type": alert["alert_type"],
                "severity": alert["severity"],
                "value": alert["value"],
                "threshold": alert["threshold"],
            }
            if alert.get("metadata"):
                payload["metadata"] = alert["metadata"]

            if self._mqtt.publish_alert(payload):
                self._db.mark_alert_synced(alert["id"])
                alert_synced += 1
            else:
                break

        # Environmental
        pending_env = self._db.get_pending_environmental(limit=self._batch_size)
        env_synced = 0
        for reading in pending_env:
            payload: dict = {"timestamp": reading["timestamp"]}
            for k in ("temperature", "humidity", "co2",
                      "gps_lat", "gps_lon", "gps_speed_kmh", "gps_moving", "gps_fix"):
                if reading.get(k) is not None:
                    payload[k] = reading[k]
            if self._mqtt.publish_environmental(payload):
                self._db.mark_environmental_synced(reading["id"])
                env_synced += 1
            else:
                break

        if alert_synced or env_synced:
            logger.info(
                f"Retry sync: {alert_synced}/{len(pending_alerts)} alerts, "
                f"{env_synced}/{len(pending_env)} environmental"
            )

    def _send_heartbeat(self) -> None:
        """Publish status heartbeat if connected."""
        if self._mqtt.is_connected:
            self._mqtt.publish_status("online")
