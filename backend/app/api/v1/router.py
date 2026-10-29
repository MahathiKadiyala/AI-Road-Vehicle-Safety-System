"""API v1 consolidated router."""
from fastapi import APIRouter
from app.api.v1.endpoints import health, hazards, damage, vehicles, risk, hospitals

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(hazards.router)
api_router.include_router(damage.router)
api_router.include_router(vehicles.router)
api_router.include_router(risk.router)
api_router.include_router(hospitals.router)
