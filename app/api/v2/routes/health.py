"""Health check routes for API v2."""

import time
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check_v2() -> Dict[str, Any]:
    """
    Health check endpoint (v2).
    
    Enhanced health check with more detailed metrics.
    """
    from app.database import Base, engine

    start_time = time.time()
    db_status = "ok"
    db_response_time = 0

    try:
        with engine.connect() as conn:
            db_start = time.time()
            conn.execute(Base.metadata.tables["payments"].select().limit(1))
            db_response_time = round((time.time() - db_start) * 1000, 2)
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "version": "v2",
        "checks": {
            "database": db_status,
            "database_response_time_ms": db_response_time,
            "total_response_time_ms": round((time.time() - start_time) * 1000, 2),
        },
    }


@router.get("/ready")
async def readiness_check_v2() -> Dict[str, Any]:
    """
    Readiness check endpoint (v2).
    
    Checks if the application is ready to serve traffic.
    """
    from app.database import Base, engine
    from app.settings import settings

    readiness_status = {
        "status": "ready",
        "version": "v2",
        "checks": {
            "database": "ok",
            "configuration": "ok",
            "celery": "ok" if settings.celery_enabled else "disabled",
        },
    }

    try:
        with engine.connect() as conn:
            conn.execute(Base.metadata.tables["payments"].select().limit(1))
    except Exception as e:
        readiness_status["status"] = "not_ready"
        readiness_status["checks"]["database"] = f"error: {str(e)}"

    return readiness_status


@router.get("/live")
async def liveness_check_v2() -> Dict[str, Any]:
    """
    Liveness check endpoint (v2).
    
    Simple check to verify the application is running.
    """
    return {
        "status": "alive",
        "version": "v2",
    }
