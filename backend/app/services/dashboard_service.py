import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.environmental import EnvironmentalReading


async def get_summary(
    db: AsyncSession, device_id: Optional[uuid.UUID] = None
) -> dict:
    cutoff = datetime.utcnow() - timedelta(hours=24)

    # Environmental averages
    env_stmt = select(
        func.avg(EnvironmentalReading.temperature).label("avg_temperature"),
        func.avg(EnvironmentalReading.humidity).label("avg_humidity"),
        func.avg(EnvironmentalReading.co2).label("avg_co2"),
    ).where(EnvironmentalReading.timestamp >= cutoff)
    if device_id is not None:
        env_stmt = env_stmt.where(EnvironmentalReading.device_id == device_id)
    env_row = (await db.execute(env_stmt)).one()

    # Latest environmental reading (most recent single row)
    latest_env_stmt = (
        select(EnvironmentalReading)
        .order_by(EnvironmentalReading.timestamp.desc())
        .limit(1)
    )
    if device_id is not None:
        latest_env_stmt = latest_env_stmt.where(
            EnvironmentalReading.device_id == device_id
        )
    latest_env = (await db.execute(latest_env_stmt)).scalars().first()

    # Alert counts by type
    alert_count_stmt = (
        select(Alert.alert_type, func.count().label("count"))
        .where(Alert.timestamp >= cutoff)
        .group_by(Alert.alert_type)
    )
    if device_id is not None:
        alert_count_stmt = alert_count_stmt.where(Alert.device_id == device_id)
    alert_counts = (await db.execute(alert_count_stmt)).all()

    # Total alerts
    total_stmt = (
        select(func.count()).select_from(Alert).where(Alert.timestamp >= cutoff)
    )
    if device_id is not None:
        total_stmt = total_stmt.where(Alert.device_id == device_id)
    total_alerts = (await db.execute(total_stmt)).scalar() or 0

    # Recent alerts
    recent_stmt = (
        select(Alert)
        .where(Alert.timestamp >= cutoff)
        .order_by(Alert.timestamp.desc())
        .limit(10)
    )
    if device_id is not None:
        recent_stmt = recent_stmt.where(Alert.device_id == device_id)
    recent_alerts = list((await db.execute(recent_stmt)).scalars().all())

    return {
        "environmental": {
            "avg_temperature": env_row.avg_temperature,
            "avg_humidity": env_row.avg_humidity,
            "avg_co2": env_row.avg_co2,
        },
        "latest_environmental": {
            "temperature": latest_env.temperature if latest_env else None,
            "humidity": latest_env.humidity if latest_env else None,
            "co2": latest_env.co2 if latest_env else None,
            "timestamp": latest_env.timestamp if latest_env else None,
        } if latest_env else None,
        "alert_counts_by_type": [
            {"alert_type": row.alert_type, "count": row.count} for row in alert_counts
        ],
        "total_alerts": total_alerts,
        "recent_alerts": recent_alerts,
    }


async def get_timeline(
    db: AsyncSession, device_id: Optional[uuid.UUID] = None
) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(hours=24)

    # Alerts
    alert_stmt = (
        select(Alert).where(Alert.timestamp >= cutoff).order_by(Alert.timestamp.desc())
    )
    if device_id is not None:
        alert_stmt = alert_stmt.where(Alert.device_id == device_id)
    alerts = list((await db.execute(alert_stmt)).scalars().all())

    # Environmental readings
    env_stmt = (
        select(EnvironmentalReading)
        .where(EnvironmentalReading.timestamp >= cutoff)
        .order_by(EnvironmentalReading.timestamp.desc())
    )
    if device_id is not None:
        env_stmt = env_stmt.where(EnvironmentalReading.device_id == device_id)
    readings = list((await db.execute(env_stmt)).scalars().all())

    # Merge into timeline
    events = []
    for alert in alerts:
        events.append(
            {
                "timestamp": alert.timestamp,
                "event_type": "alert",
                "device_id": alert.device_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "value": alert.value,
            }
        )
    for reading in readings:
        events.append(
            {
                "timestamp": reading.timestamp,
                "event_type": "environmental",
                "device_id": reading.device_id,
                "temperature": reading.temperature,
                "humidity": reading.humidity,
                "co2": reading.co2,
            }
        )

    events.sort(key=lambda e: e["timestamp"], reverse=True)
    return events


async def get_history(
    db: AsyncSession,
    start_date: datetime,
    end_date: datetime,
    group_by: str = "hour",
    device_id: Optional[uuid.UUID] = None,
) -> dict:
    date_filter = and_(
        EnvironmentalReading.timestamp >= start_date,
        EnvironmentalReading.timestamp <= end_date,
    )
    alert_date_filter = and_(
        Alert.timestamp >= start_date,
        Alert.timestamp <= end_date,
    )

    # Environmental data grouped by period
    env_period = func.date_trunc(group_by, EnvironmentalReading.timestamp).label(
        "period"
    )
    env_stmt = (
        select(
            env_period,
            func.avg(EnvironmentalReading.temperature).label("avg_temperature"),
            func.avg(EnvironmentalReading.humidity).label("avg_humidity"),
            func.avg(EnvironmentalReading.co2).label("avg_co2"),
        )
        .where(date_filter)
        .group_by(env_period)
        .order_by(env_period)
    )
    if device_id is not None:
        env_stmt = env_stmt.where(EnvironmentalReading.device_id == device_id)

    # Alert counts grouped by same period
    alert_period = func.date_trunc(group_by, Alert.timestamp).label("period")
    alert_stmt = (
        select(alert_period, func.count().label("alert_count"))
        .where(alert_date_filter)
        .group_by(alert_period)
        .order_by(alert_period)
    )
    if device_id is not None:
        alert_stmt = alert_stmt.where(Alert.device_id == device_id)

    env_rows = (await db.execute(env_stmt)).all()
    alert_rows = (await db.execute(alert_stmt)).all()

    # Merge by period
    data_map: dict[str, dict] = {}

    for row in env_rows:
        key = row.period.isoformat()
        data_map[key] = {
            "period": key,
            "avg_temperature": row.avg_temperature,
            "avg_humidity": row.avg_humidity,
            "avg_co2": row.avg_co2,
            "alert_count": 0,
        }

    for row in alert_rows:
        key = row.period.isoformat()
        if key in data_map:
            data_map[key]["alert_count"] = row.alert_count
        else:
            data_map[key] = {
                "period": key,
                "avg_temperature": None,
                "avg_humidity": None,
                "avg_co2": None,
                "alert_count": row.alert_count,
            }

    sorted_data = sorted(data_map.values(), key=lambda d: d["period"])

    return {
        "group_by": group_by,
        "start_date": start_date,
        "end_date": end_date,
        "data": sorted_data,
    }
