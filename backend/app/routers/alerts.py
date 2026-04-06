from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.enums import AlertType, Severity
from app.schemas.alert import AlertCreate, AlertResponse
from app.services import alert_service, notification_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/", response_model=AlertResponse, status_code=201)
async def create_alert(data: AlertCreate, db: AsyncSession = Depends(get_db)):
    alert = await alert_service.create_alert(db, data)
    if not alert:
        raise HTTPException(status_code=404, detail="Device not found")
    # RF8: trigger notification check
    await notification_service.check_and_create_notification(db, data.device_id)
    return alert


@router.get("/", response_model=list[AlertResponse])
async def list_alerts(
    device_id: Optional[UUID] = None,
    alert_type: Optional[AlertType] = None,
    severity: Optional[Severity] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await alert_service.get_alerts(
        db, device_id, alert_type, severity, start_date, end_date, skip, limit
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: UUID, db: AsyncSession = Depends(get_db)):
    alert = await alert_service.get_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert
