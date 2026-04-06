from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.dashboard import DashboardSummary, HistoryResponse, TimelineEvent
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    device_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_service.get_summary(db, device_id)


@router.get("/timeline", response_model=list[TimelineEvent])
async def get_timeline(
    device_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_service.get_timeline(db, device_id)


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    group_by: Literal["hour", "day", "month"] = Query("hour"),
    device_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_service.get_history(
        db, start_date, end_date, group_by, device_id
    )
