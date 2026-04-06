from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.environmental import EnvironmentalReadingCreate, EnvironmentalReadingResponse
from app.services import environmental_service

router = APIRouter(prefix="/environmental", tags=["environmental"])


@router.post("/", response_model=EnvironmentalReadingResponse, status_code=201)
async def create_reading(
    data: EnvironmentalReadingCreate, db: AsyncSession = Depends(get_db)
):
    reading = await environmental_service.create_reading(db, data)
    if not reading:
        raise HTTPException(status_code=404, detail="Device not found")
    return reading


@router.get("/", response_model=list[EnvironmentalReadingResponse])
async def list_readings(
    device_id: Optional[UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await environmental_service.get_readings(
        db, device_id, start_date, end_date, skip, limit
    )


@router.get("/{reading_id}", response_model=EnvironmentalReadingResponse)
async def get_reading(reading_id: UUID, db: AsyncSession = Depends(get_db)):
    reading = await environmental_service.get_reading(db, reading_id)
    if not reading:
        raise HTTPException(
            status_code=404, detail="Environmental reading not found"
        )
    return reading
