"""
Finance Dashboard API — Application Entry Point (Composition Root)

Production improvements:
- Enhanced /health endpoint: checks real DB connectivity (not just a static "ok")
- Startup uses exponential backoff retry for DB table creation
- Startup validates that JWT_SECRET_KEY has been changed from the default
- Debug-mode warning to prevent DEBUG=true in production
"""

import logging
import warnings
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, dashboard, financial_records, users
from app.core.config import get_settings
from app.domain.database import check_db_connection, create_tables_with_retry
from app.middleware.error_handler import register_error_handlers

# Configure structured logging (ship to ELK/Sentry in production)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

_DEFAULT_SECRET = "change-me-in-production-use-openssl-rand-hex-32"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — startup and shutdown logic."""
    logger.info("Starting %s v%s…", settings.APP_NAME, settings.APP_VERSION)

    # Security: warn loudly if the JWT secret is still the insecure default
    if settings.JWT_SECRET_KEY.get_secret_value() == _DEFAULT_SECRET:
        warnings.warn(
            "JWT_SECRET_KEY is set to the insecure default value! "
            "Generate a strong key: python -c \"import secrets; print(secrets.token_hex(32))\"",
            stacklevel=1,
        )

    if settings.DEBUG:
        logger.warning(
            "DEBUG mode is ON — never run with DEBUG=true in production!"
        )

    # DB startup with exponential backoff retry
    await create_tables_with_retry()
    logger.info("Application startup complete.")
    yield
    logger.info("Shutting down %s…", settings.APP_NAME)


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
    """Root endpoint — application information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "healthy",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Deep health check endpoint for monitoring and load balancers.

    Checks:
    - Database connectivity (real SELECT 1 probe, not a static flag)

    Returns 200 if all subsystems are healthy, 503 if any are degraded.
    """
    db_ok = await check_db_connection()

    status = "ok" if db_ok else "degraded"
    http_status = 200 if db_ok else 503

    payload = {
        "status": status,
        "version": settings.APP_VERSION,
        "subsystems": {
            "database": "ok" if db_ok else "error",
        },
    }

    from fastapi.responses import JSONResponse
    return JSONResponse(content=payload, status_code=http_status)
