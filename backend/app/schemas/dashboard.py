from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import AlertType, Severity


class AlertCountByType(BaseModel):
    alert_type: AlertType
    count: int


class EnvironmentalAverages(BaseModel):
    avg_temperature: Optional[float] = None
    avg_humidity: Optional[float] = None
    avg_co2: Optional[float] = None


class RecentAlert(BaseModel):
    id: UUID
    device_id: UUID
    alert_type: AlertType
    severity: Severity
    value: float
    threshold: float
    timestamp: datetime

    model_config = {"from_attributes": True}


class DashboardSummary(BaseModel):
    environmental: EnvironmentalAverages
    alert_counts_by_type: list[AlertCountByType]
    total_alerts: int
    recent_alerts: list[RecentAlert]


class TimelineEvent(BaseModel):
    timestamp: datetime
    event_type: str
    device_id: UUID
    alert_type: Optional[AlertType] = None
    severity: Optional[Severity] = None
    value: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    co2: Optional[float] = None


class HistoryDataPoint(BaseModel):
    period: str
    avg_temperature: Optional[float] = None
    avg_humidity: Optional[float] = None
    avg_co2: Optional[float] = None
    alert_count: int = 0


class HistoryResponse(BaseModel):
    group_by: str
    start_date: datetime
    end_date: datetime
    data: list[HistoryDataPoint]
