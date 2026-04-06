from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import AlertType, Severity


class AlertBase(BaseModel):
    device_id: UUID
    alert_type: AlertType
    severity: Severity
    value: float
    threshold: float


class AlertCreate(AlertBase):
    metadata: Optional[dict[str, Any]] = None


class AlertResponse(AlertBase):
    id: UUID
    timestamp: datetime
    synced_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = Field(
        default=None, validation_alias="metadata_"
    )

    model_config = {"from_attributes": True, "populate_by_name": True}
