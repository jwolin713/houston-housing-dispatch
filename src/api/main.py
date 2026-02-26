"""FastAPI application for the Houston Housing Dispatch approval workflow."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.database import init_db

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("Starting Houston Housing Dispatch API")
    init_db()
    yield
    # Shutdown
    logger.info("Shutting down Houston Housing Dispatch API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Houston Housing Dispatch",
        description="Newsletter automation and approval workflow",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict to your domain
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and include routers
    from src.api.routes.approval import router as approval_router
    from src.api.routes.dashboard import router as dashboard_router
    from src.api.routes.health import router as health_router

    app.include_router(health_router, prefix="/health", tags=["Health"])
    app.include_router(approval_router, prefix="/approve", tags=["Approval"])
    app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])

    return app


# Create the app instance
app = create_app()
