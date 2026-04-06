import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.device import Device
from app.models.enums import AlertType, Severity
from app.schemas.alert import AlertCreate


async def create_alert(db: AsyncSession, data: AlertCreate) -> Alert | None:
    device = await db.get(Device, data.device_id)
    if not device:
        return None

    data_dict = data.model_dump(exclude={"metadata"})
    alert = Alert(**data_dict, metadata_=data.metadata)
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def get_alert(db: AsyncSession, alert_id: uuid.UUID) -> Alert | None:
    return await db.get(Alert, alert_id)


async def get_alerts(
    db: AsyncSession,
    device_id: Optional[uuid.UUID] = None,
    alert_type: Optional[AlertType] = None,
    severity: Optional[Severity] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Alert]:
    limit = min(limit, 1000)
    stmt = select(Alert)

    if device_id is not None:
        stmt = stmt.where(Alert.device_id == device_id)
    if alert_type is not None:
        stmt = stmt.where(Alert.alert_type == alert_type)
    if severity is not None:
        stmt = stmt.where(Alert.severity == severity)
    if start_date is not None:
        stmt = stmt.where(Alert.timestamp >= start_date)
    if end_date is not None:
        stmt = stmt.where(Alert.timestamp <= end_date)

    stmt = stmt.order_by(Alert.timestamp.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
