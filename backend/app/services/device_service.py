import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.schemas.device import DeviceCreate


async def create_device(db: AsyncSession, data: DeviceCreate) -> Device:
    device = Device(**data.model_dump())
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


async def get_device(db: AsyncSession, device_id: uuid.UUID) -> Device | None:
    return await db.get(Device, device_id)


async def get_devices(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[Device]:
    limit = min(limit, 1000)
    stmt = select(Device).order_by(Device.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_device(
    db: AsyncSession, device_id: uuid.UUID, updates: dict
) -> Device | None:
    device = await db.get(Device, device_id)
    if not device:
        return None
    for key, value in updates.items():
        setattr(device, key, value)
    device.last_seen_at = datetime.utcnow()
    await db.commit()
    await db.refresh(device)
    return device


async def delete_device(db: AsyncSession, device_id: uuid.UUID) -> bool:
    device = await db.get(Device, device_id)
    if not device:
        return False
    await db.delete(device)
    await db.commit()
    return True
