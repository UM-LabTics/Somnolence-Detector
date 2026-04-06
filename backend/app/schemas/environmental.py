from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class EnvironmentalReadingBase(BaseModel):
    device_id: UUID
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    co2: Optional[float] = None


class EnvironmentalReadingCreate(EnvironmentalReadingBase):
    pass


class EnvironmentalReadingResponse(EnvironmentalReadingBase):
    id: UUID
    timestamp: datetime
    synced_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
