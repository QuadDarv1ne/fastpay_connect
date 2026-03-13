"""Health check routes for API v1."""

from fastapi import APIRouter
from typing import Dict, Any
import time

router = APIRouter()


@router.get("/health")
async def health_check_v1() -> Dict[str, Any]:
    """Health check endpoint (v1)."""
    from app.database import engine, Base
    
    start_time = time.time()
    db_status = "ok"
    
    try:
        with engine.connect() as conn:
            conn.execute(Base.metadata.tables["payments"].select().limit(1))
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "version": "v1",
        "checks": {
            "database": db_status,
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }
    }


@router.get("/ready")
async def readiness_check_v1() -> Dict[str, Any]:
    """Readiness check endpoint (v1)."""
    from app.database import engine, Base
    from app.settings import settings
    
    readiness_status = {
        "status": "ready",
        "version": "v1",
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


@router.get("/celery")
async def celery_health_check_v1() -> Dict[str, Any]:
    """Celery health check endpoint (v1)."""
    from app.settings import settings
    
    if not settings.celery_enabled:
        return {"status": "disabled", "version": "v1", "message": "Celery is disabled"}
    
    try:
        from app.tasks.webhook_tasks import health_check as celery_health_task
        result = celery_health_task.delay()
        result_value = result.get(timeout=10)
        
        return {
            "status": "healthy",
            "version": "v1",
            "celery": result_value,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "version": "v1",
            "message": f"Celery health check failed: {str(e)}",
        }
