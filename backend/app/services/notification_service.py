import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.alert import Alert
from app.models.notification import AlertNotification


async def check_and_create_notification(
    db: AsyncSession, device_id: uuid.UUID
) -> AlertNotification | None:
    window_start = datetime.utcnow() - timedelta(
        minutes=settings.ALERT_THRESHOLD_WINDOW_MINUTES
    )

    # Count alerts in window
    count_stmt = (
        select(func.count())
        .select_from(Alert)
        .where(and_(Alert.device_id == device_id, Alert.timestamp >= window_start))
    )
    count = (await db.execute(count_stmt)).scalar() or 0

    if count < settings.ALERT_THRESHOLD_COUNT:
        return None

    # Check for existing recent notification (avoid duplicates)
    existing_stmt = (
        select(AlertNotification.id)
        .where(
            and_(
                AlertNotification.device_id == device_id,
                AlertNotification.created_at >= window_start,
            )
        )
        .limit(1)
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None:
        return None

    # Get alert IDs in window
    ids_stmt = select(Alert.id).where(
        and_(Alert.device_id == device_id, Alert.timestamp >= window_start)
    )
    alert_ids = [str(aid) for aid in (await db.execute(ids_stmt)).scalars().all()]

    notification = AlertNotification(
        device_id=device_id,
        alert_count=count,
        time_window_minutes=settings.ALERT_THRESHOLD_WINDOW_MINUTES,
        alert_ids=alert_ids,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


async def get_notifications(
    db: AsyncSession,
    device_id: Optional[uuid.UUID] = None,
    acknowledged: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[AlertNotification]:
    limit = min(limit, 1000)
    stmt = select(AlertNotification)

    if device_id is not None:
        stmt = stmt.where(AlertNotification.device_id == device_id)
    if acknowledged is not None:
        stmt = stmt.where(AlertNotification.acknowledged == acknowledged)

    stmt = stmt.order_by(AlertNotification.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_notification(
    db: AsyncSession, notification_id: uuid.UUID
) -> AlertNotification | None:
    return await db.get(AlertNotification, notification_id)


async def acknowledge_notification(
    db: AsyncSession, notification_id: uuid.UUID
) -> AlertNotification | None:
    notification = await db.get(AlertNotification, notification_id)
    if not notification:
        return None
    notification.acknowledged = True
    await db.commit()
    await db.refresh(notification)
    return notification
