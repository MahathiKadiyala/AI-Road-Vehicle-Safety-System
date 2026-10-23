"""Hospital ORM model for verified medical and trauma center reference data."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry

from app.core.database import Base


class Hospital(Base):
    """Database model for emergency hospital locations."""
    __tablename__ = "hospitals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(180), nullable=False)
    facility_type = Column(String(80), nullable=False, default="General Hospital")
    
    # Coordinate pair for general serialization
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # PostGIS Spatial Point (SRID 4326 = WGS84 standard GPS)
    geom = Column(Geometry(geometry_type="POINT", srid=4326, nullable=True))
    
    address = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    has_emergency_service = Column(Boolean, nullable=False, default=True)
    
    # Explicitly labeled reference capacity (not live telemetry in MVP)
    total_beds_reference = Column(Integer, nullable=True)
    is_verified_facility = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_hospitals_lat_lon", "latitude", "longitude"),
        Index("idx_hospitals_emergency", "has_emergency_service"),
    )

    def __repr__(self) -> str:
        return f"<Hospital(id={self.id}, name='{self.name}', emergency={self.has_emergency_service})>"
