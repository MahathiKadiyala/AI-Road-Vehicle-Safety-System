"""ORM Models for AI-Powered Road and Vehicle Safety System."""
from app.core.database import Base
from app.models.hazard import Hazard
from app.models.vehicle import VehicleAssessment
from app.models.hospital import Hospital

__all__ = ["Base", "Hazard", "VehicleAssessment", "Hospital"]
