"""Hazard ORM model representing reported road surface distress and obstacles."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry

from app.core.database import Base


class Hazard(Base):
    """Database model for road hazards."""
    __tablename__ = "hazards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    hazard_type = Column(String(50), nullable=False, default="pothole")
    severity = Column(String(20), nullable=False, default="medium")
    
    # Coordinate pair for general serialization
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # PostGIS Spatial Point (SRID 4326 = WGS84 standard GPS)
    geom = Column(Geometry(geometry_type="POINT", srid=4326, nullable=True))
    
    image_path = Column(String(255), nullable=True)
    source = Column(String(50), nullable=False, default="citizen_report")
    status = Column(String(30), nullable=False, default="reported")
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_hazards_lat_lon", "latitude", "longitude"),
        Index("idx_hazards_status", "status"),
        Index("idx_hazards_severity", "severity"),
    )

    def __repr__(self) -> str:
        return f"<Hazard(id={self.id}, type={self.hazard_type}, severity={self.severity}, status={self.status})>"
