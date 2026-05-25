import asyncio
import json
import logging
import os
import ssl
import time
import uuid

import paho.mqtt.client as mqtt

from app.config import settings
from app.mqtt.handlers import handle_alert, handle_environmental, handle_status

logger = logging.getLogger(__name__)

# Topic patterns (with + wildcard for device_id)
TOPIC_ALERTS = f"{settings.MQTT_TOPIC_PREFIX}/+/alerts"
TOPIC_ENVIRONMENTAL = f"{settings.MQTT_TOPIC_PREFIX}/+/environmental"
TOPIC_STATUS = f"{settings.MQTT_TOPIC_PREFIX}/+/status"


def _on_connect(client, userdata, connect_flags, reason_code, properties):
    """Called on (re)connect. Subscribe to all topics."""
    logger.info(f"MQTT connected: {reason_code}")
    client.subscribe(
        [
            (TOPIC_ALERTS, 1),
            (TOPIC_ENVIRONMENTAL, 1),
            (TOPIC_STATUS, 1),
        ]
    )
    logger.info(
        f"MQTT subscribed to: {TOPIC_ALERTS}, {TOPIC_ENVIRONMENTAL}, {TOPIC_STATUS}"
    )


def _on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    """Called on disconnect. Paho auto-reconnects via reconnect_delay_set."""
    logger.warning(f"MQTT disconnected: {reason_code}")


def _log_handler_exception(future):
    """Done-callback to log errors from async handlers."""
    exc = future.exception()
    if exc:
        logger.error(f"MQTT handler error: {exc}", exc_info=exc)


def _on_message(client, userdata, message):
    """Sync callback → schedules async handler on the event loop."""
    try:
        topic = message.topic
        parts = topic.split("/")

        if len(parts) != 3 or parts[0] != settings.MQTT_TOPIC_PREFIX:
            logger.warning(f"Unknown topic format: {topic}")
            return

        device_id_str = parts[1]
        message_type = parts[2]

        try:
            payload = json.loads(message.payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning(f"Invalid JSON on topic {topic}")
            return

        # Select handler
        handlers = {
            "alerts": handle_alert,
            "environmental": handle_environmental,
            "status": handle_status,
        }

        handler = handlers.get(message_type)
        if not handler:
            logger.warning(f"Unknown message type: {message_type}")
            return

        # Schedule async handler on FastAPI's event loop (fire-and-forget)
        loop = userdata["loop"]
        future = asyncio.run_coroutine_threadsafe(
            handler(device_id_str, payload), loop
        )
        future.add_done_callback(_log_handler_exception)

    except Exception:
        logger.exception("Error in MQTT on_message callback")


def create_mqtt_client(loop: asyncio.AbstractEventLoop) -> mqtt.Client:
    """Create and configure the MQTT client."""
    # clientId único por proceso. AWS IoT permite una sola conexión por clientId
    # y kickea las duplicadas: durante un rolling deploy de ECS la tarea vieja y
    # la nueva conviven, y si comparten clientId se desconectan entre sí en loop.
    # El sufijo aleatorio evita la colisión. Requiere que la IoT Policy permita
    # client/somnolence-backend-*.
    client_id = os.getenv("MQTT_CLIENT_ID", f"somnolence-backend-{uuid.uuid4().hex[:8]}")
    logger.info(f"MQTT client_id: {client_id}")

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
        userdata={"loop": loop},
    )

    # --- TLS para AWS IoT Core ---
    # Si las rutas de los certificados estan definidas, activar TLS.
    # En local (Mosquitto) estas variables no existen y se conecta sin TLS.
    ca = os.getenv("MQTT_CA_CERT")
    cert = os.getenv("MQTT_CLIENT_CERT")
    key = os.getenv("MQTT_CLIENT_KEY")
    if ca and cert and key:
        client.tls_set(
            ca_certs=ca,
            certfile=cert,
            keyfile=key,
            tls_version=ssl.PROTOCOL_TLSv1_2,
        )
        logger.info("MQTT TLS habilitado (AWS IoT Core)")
    else:
        logger.info("MQTT sin TLS (modo local)")
    # --- fin TLS ---

    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect
    client.on_message = _on_message

    client.reconnect_delay_set(min_delay=1, max_delay=60)

    return client


def start_mqtt(loop: asyncio.AbstractEventLoop) -> mqtt.Client:
    """Create, connect, and start the MQTT client."""
    client = create_mqtt_client(loop)

    # Retry connection in case broker isn't ready yet
    for attempt in range(5):
        try:
            client.connect(settings.MQTT_BROKER, settings.MQTT_PORT)
            logger.info(
                f"MQTT connecting to {settings.MQTT_BROKER}:{settings.MQTT_PORT}"
            )
            break
        except (ConnectionRefusedError, OSError) as e:
            if attempt < 4:
                logger.warning(
                    f"MQTT connection attempt {attempt + 1}/5 failed: {e}. "
                    f"Retrying in 2s..."
                )
                time.sleep(2)
            else:
                logger.error("MQTT connection failed after 5 attempts")
                raise

    client.loop_start()
    return client


def stop_mqtt(client: mqtt.Client) -> None:
    """Stop and disconnect the MQTT client."""
    logger.info("Stopping MQTT client...")
    client.loop_stop()
    client.disconnect()
    logger.info("MQTT client stopped")