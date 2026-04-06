import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.environmental import EnvironmentalReading
from app.schemas.environmental import EnvironmentalReadingCreate


async def create_reading(
    db: AsyncSession, data: EnvironmentalReadingCreate
) -> EnvironmentalReading | None:
    device = await db.get(Device, data.device_id)
    if not device:
        return None

    reading = EnvironmentalReading(**data.model_dump())
    db.add(reading)
    await db.commit()
    await db.refresh(reading)
    return reading


async def get_reading(
    db: AsyncSession, reading_id: uuid.UUID
) -> EnvironmentalReading | None:
    return await db.get(EnvironmentalReading, reading_id)


async def get_readings(
    db: AsyncSession,
    device_id: Optional[uuid.UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[EnvironmentalReading]:
    limit = min(limit, 1000)
    stmt = select(EnvironmentalReading)

    if device_id is not None:
        stmt = stmt.where(EnvironmentalReading.device_id == device_id)
    if start_date is not None:
        stmt = stmt.where(EnvironmentalReading.timestamp >= start_date)
    if end_date is not None:
        stmt = stmt.where(EnvironmentalReading.timestamp <= end_date)

    stmt = (
        stmt.order_by(EnvironmentalReading.timestamp.desc()).offset(skip).limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
