"""FastAPI Application Entry Point."""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.router import api_router
from app.api.v1.endpoints.health import get_health_status
from app.schemas.health import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("roadsafety.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"Starting {settings.PROJECT_NAME} (v{settings.VERSION})...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Debug: {settings.DEBUG}")

    # Ensure uploads directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Initialize database tables and PostGIS extension safely
    logger.info("Initializing database connectivity...")
    init_res = await init_db()
    if init_res.get("tables_created"):
        logger.info("Database tables verified/created successfully.")
    else:
        logger.warning(f"Database initialization status: {init_res.get('error')}")

    yield

    logger.info("Shutting down application...")


# FastAPI Application Instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "AI-Powered Road and Vehicle Safety System backend API. "
        "Provides road hazard tracking, preliminary vehicle assessment, "
        "and emergency hospital advisory services."
    ),
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root-level health endpoint for easy monitoring (GET /health)
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def root_health():
    """Root health endpoint."""
    return await get_health_status()

# Include API v1 routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Mount static uploads if available
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/static/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
