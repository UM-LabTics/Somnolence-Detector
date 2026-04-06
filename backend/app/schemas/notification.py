from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AlertNotificationBase(BaseModel):
    device_id: UUID
    alert_count: int
    time_window_minutes: int
    alert_ids: list[Any]


class AlertNotificationCreate(AlertNotificationBase):
    pass


class AlertNotificationResponse(AlertNotificationBase):
    id: UUID
    created_at: datetime
    acknowledged: bool

    model_config = {"from_attributes": True}
