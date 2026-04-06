import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import AlertType, Severity


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id"))
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType))
    severity: Mapped[Severity] = mapped_column(Enum(Severity))
    value: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    # "metadata" clashes with SQLAlchemy's internal Base.metadata attribute,
    # so we use metadata_ as the Python name mapped to the "metadata" SQL column.
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=True)

    device = relationship("Device", back_populates="alerts")
