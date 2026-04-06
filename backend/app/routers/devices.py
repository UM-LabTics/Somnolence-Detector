from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.device import DeviceCreate, DeviceResponse, DeviceUpdate
from app.services import device_service

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/", response_model=DeviceResponse, status_code=201)
async def create_device(
    data: DeviceCreate, db: AsyncSession = Depends(get_db)
):
    return await device_service.create_device(db, data)


@router.get("/", response_model=list[DeviceResponse])
async def list_devices(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    return await device_service.get_devices(db, skip, limit)


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: UUID, db: AsyncSession = Depends(get_db)):
    device = await device_service.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: UUID, data: DeviceUpdate, db: AsyncSession = Depends(get_db)
):
    device = await device_service.update_device(
        db, device_id, data.model_dump(exclude_unset=True)
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: UUID, db: AsyncSession = Depends(get_db)):
    deleted = await device_service.delete_device(db, device_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Device not found")
