from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DeviceBase(BaseModel):
    name: str


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class DeviceResponse(DeviceBase):
    id: UUID
    created_at: datetime
    last_seen_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}
