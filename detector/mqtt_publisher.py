"""MQTT publisher client for the Somnolence Detector."""

import json
import logging
import threading
import time

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTPublisher:
    """MQTT client wrapper for publishing detection data."""

    def __init__(
        self,
        broker: str,
        port: int,
        device_id: str,
        prefix: str = "somnolence",
    ):
        self._broker = broker
        self._port = port
        self._device_id = device_id
        self._prefix = prefix
        self._connected = threading.Event()

        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.reconnect_delay_set(min_delay=1, max_delay=60)

        # Last Will: mark device offline on unexpected disconnect
        status_topic = f"{prefix}/{device_id}/status"
        self._client.will_set(
            status_topic, json.dumps({"status": "offline"}), qos=1
        )

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    def connect(self) -> None:
        for attempt in range(3):
            try:
                self._client.connect(self._broker, self._port)
                self._client.loop_start()
                logger.info(
                    f"MQTT connecting to {self._broker}:{self._port}"
                )
                return
            except (ConnectionRefusedError, OSError) as e:
                if attempt < 2:
                    logger.warning(
                        f"MQTT connection attempt {attempt + 1}/3 failed: {e}"
                    )
                    time.sleep(2)
                else:
                    logger.error(
                        "MQTT connection failed after 3 attempts, "
                        "will auto-reconnect in background"
                    )
                    # Start loop anyway for auto-reconnect
                    self._client.loop_start()

    def disconnect(self) -> None:
        logger.info("MQTT publisher disconnecting...")
        self._client.loop_stop()
        self._client.disconnect()
        self._connected.clear()

    def publish_alert(self, payload: dict) -> bool:
        topic = f"{self._prefix}/{self._device_id}/alerts"
        return self._publish(topic, payload)

    def publish_environmental(self, payload: dict) -> bool:
        topic = f"{self._prefix}/{self._device_id}/environmental"
        return self._publish(topic, payload)

    def publish_status(self, status: str = "online") -> bool:
        topic = f"{self._prefix}/{self._device_id}/status"
        return self._publish(topic, {"status": status})

    def _publish(self, topic: str, payload: dict) -> bool:
        if not self._connected.is_set():
            return False
        try:
            result = self._client.publish(
                topic, json.dumps(payload), qos=1
            )
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            logger.error(f"MQTT publish error: {e}")
            return False

    def _on_connect(self, client, userdata, connect_flags, reason_code, properties):
        if reason_code == 0:
            self._connected.set()
            logger.info("MQTT publisher connected")
        else:
            self._connected.clear()
            logger.warning(f"MQTT connection failed: {reason_code}")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self._connected.clear()
        logger.warning(f"MQTT publisher disconnected: {reason_code}")
