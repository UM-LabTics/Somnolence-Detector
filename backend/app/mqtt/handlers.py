import logging
import uuid
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.device import Device
from app.models.enums import AlertType, Severity
from app.schemas.alert import AlertCreate
from app.schemas.environmental import EnvironmentalReadingCreate
from app.services import alert_service, environmental_service, notification_service

logger = logging.getLogger(__name__)


async def _ensure_device(db: AsyncSession, device_id: uuid.UUID) -> Device:
    """Ensure device exists and update last_seen. Auto-register if needed."""
    device = await db.get(Device, device_id)
    if device:
        device.last_seen_at = datetime.utcnow()
        device.is_active = True
        await db.commit()
        return device

    # Auto-register new device
    device = Device(id=device_id, name=f"Device-{str(device_id)[:8]}")
    db.add(device)
    try:
        await db.commit()
        await db.refresh(device)
        logger.info(f"Auto-registered device: {device_id}")
        return device
    except IntegrityError:
        # Race condition: another message already registered this device
        await db.rollback()
        device = await db.get(Device, device_id)
        if device:
            device.last_seen_at = datetime.utcnow()
            device.is_active = True
            await db.commit()
            return device
        raise


async def handle_alert(device_id_str: str, payload: dict) -> None:
    """Handle an alert message from MQTT."""
    try:
        device_id = uuid.UUID(device_id_str)
    except ValueError:
        logger.warning(f"Invalid device_id: {device_id_str}")
        return

    try:
        async with async_session() as db:
            await _ensure_device(db, device_id)

            alert_data = AlertCreate(
                device_id=device_id,
                alert_type=AlertType(payload["alert_type"]),
                severity=Severity(payload["severity"]),
                value=payload["value"],
                threshold=payload["threshold"],
                metadata=payload.get("metadata"),
            )

            alert = await alert_service.create_alert(db, alert_data)
            if alert:
                # RF8: check notification threshold
                await notification_service.check_and_create_notification(
                    db, device_id
                )
                logger.info(
                    f"Alert created: {alert.alert_type.value} "
                    f"from device {device_id_str[:8]}"
                )
    except (KeyError, ValueError, ValidationError) as e:
        logger.warning(f"Invalid alert payload: {e}")
    except Exception:
        logger.exception(f"Error handling alert from device {device_id_str[:8]}")


async def handle_environmental(device_id_str: str, payload: dict) -> None:
    """Handle an environmental reading message from MQTT."""
    try:
        device_id = uuid.UUID(device_id_str)
    except ValueError:
        logger.warning(f"Invalid device_id: {device_id_str}")
        return

    try:
        async with async_session() as db:
            await _ensure_device(db, device_id)

            reading_data = EnvironmentalReadingCreate(
                device_id=device_id,
                temperature=payload.get("temperature"),
                humidity=payload.get("humidity"),
                co2=payload.get("co2"),
            )

            reading = await environmental_service.create_reading(db, reading_data)
            if reading:
                logger.info(
                    f"Environmental reading from device {device_id_str[:8]}: "
                    f"temp={reading.temperature} hum={reading.humidity} "
                    f"co2={reading.co2}"
                )
    except (KeyError, ValueError, ValidationError) as e:
        logger.warning(f"Invalid environmental payload: {e}")
    except Exception:
        logger.exception(
            f"Error handling environmental from device {device_id_str[:8]}"
        )


async def handle_status(device_id_str: str, payload: dict) -> None:
    """Handle a status/heartbeat message from MQTT."""
    try:
        device_id = uuid.UUID(device_id_str)
    except ValueError:
        logger.warning(f"Invalid device_id: {device_id_str}")
        return

    try:
        async with async_session() as db:
            await _ensure_device(db, device_id)
            logger.debug(
                f"Status from device {device_id_str[:8]}: "
                f"{payload.get('status', 'unknown')}"
            )
    except Exception:
        logger.exception(f"Error handling status from device {device_id_str[:8]}")
