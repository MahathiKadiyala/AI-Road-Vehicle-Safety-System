"""Vehicle Assessment ORM model for preliminary rule-based condition checks."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class VehicleAssessment(Base):
    """Database model for preliminary vehicle safety assessments."""
    __tablename__ = "vehicle_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    make = Column(String(80), nullable=False)
    model = Column(String(80), nullable=False)
    year = Column(Integer, nullable=False)
    odometer_km = Column(Float, nullable=False)
    
    # Critical mechanical measurements
    brake_pad_thickness_mm = Column(Float, nullable=False)
    tyre_tread_depth_mm = Column(Float, nullable=False)
    service_records_count = Column(Integer, nullable=False, default=0)
    past_accidents_count = Column(Integer, nullable=False, default=0)

    # Assessment outputs
    preliminary_score = Column(Float, nullable=False)  # 0.0 to 100.0
    risk_tier = Column(String(30), nullable=False)     # Low, Moderate, High, Critical
    critical_warnings = Column(JSON, nullable=False, default=list)
    legal_disclaimer_version = Column(String(50), nullable=False, default="CMVR-Preliminary-v1.0")
    disclaimer_acknowledged = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_vehicle_risk_tier", "risk_tier"),
        Index("idx_vehicle_score", "preliminary_score"),
    )

    def __repr__(self) -> str:
        return f"<VehicleAssessment(id={self.id}, vehicle='{self.year} {self.make} {self.model}', score={self.preliminary_score}, tier={self.risk_tier})>"
