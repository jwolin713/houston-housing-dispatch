"""Health check endpoints."""

from datetime import datetime

import structlog
from fastapi import APIRouter

from src.auth.cookie_manager import CookieManager
from src.publishers.substack_client import SubstackClient

logger = structlog.get_logger()
router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "houston-housing-dispatch",
    }


@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check including external services."""
    # Check Substack
    try:
        substack = SubstackClient()
        substack_health = substack.check_health()
    except Exception as e:
        substack_health = {"healthy": False, "error": str(e)}

    # Check cookie status
    try:
        cookies = CookieManager()
        cookie_health = cookies.check_health()
    except Exception as e:
        cookie_health = {"healthy": False, "error": str(e)}

    overall_healthy = substack_health.get("healthy", False)

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "substack": substack_health,
            "cookies": cookie_health,
        },
    }
