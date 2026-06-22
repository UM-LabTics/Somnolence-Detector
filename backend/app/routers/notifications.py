from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.schemas.notification import AlertNotificationResponse
from app.services import notification_service

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/", response_model=list[AlertNotificationResponse])
async def list_notifications(
    device_id: Optional[UUID] = None,
    acknowledged: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.get_notifications(
        db, device_id, acknowledged, skip, limit
    )


@router.get("/{notification_id}", response_model=AlertNotificationResponse)
async def get_notification(
    notification_id: UUID, db: AsyncSession = Depends(get_db)
):
    notification = await notification_service.get_notification(db, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.patch(
    "/{notification_id}/acknowledge",
    response_model=AlertNotificationResponse,
)
async def acknowledge_notification(
    notification_id: UUID, db: AsyncSession = Depends(get_db)
):
    notification = await notification_service.acknowledge_notification(
        db, notification_id
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification
