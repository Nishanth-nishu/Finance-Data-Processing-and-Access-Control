"""
Finance Dashboard API — Application Entry Point (Composition Root)

This is the composition root where all components are wired together.
Follows the Dependency Inversion Principle: this module depends on
abstractions (routers), not concrete implementations.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, dashboard, financial_records, users
from app.core.config import get_settings
from app.domain.database import create_tables
from app.middleware.error_handler import register_error_handlers

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — startup and shutdown logic."""
    logger.info("Starting Finance Dashboard API...")
    await create_tables()
    logger.info("Database tables created successfully")
    yield
    logger.info("Shutting down Finance Dashboard API...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "A production-grade backend for a finance dashboard system with "
        "role-based access control, financial record management, and "
        "analytics APIs. Built with Clean Architecture and SOLID principles."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register global error handlers
register_error_handlers(app)

# --- API Routes (versioned) ---
API_V1_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(users.router, prefix=API_V1_PREFIX)
app.include_router(financial_records.router, prefix=API_V1_PREFIX)
app.include_router(dashboard.router, prefix=API_V1_PREFIX)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint — health check / welcome."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "healthy",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok"}
