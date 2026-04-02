"""
Global error handler middleware — maps custom exceptions to HTTP responses.
Provides structured JSON error format with no stack trace leakage.
"""

import logging
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    DuplicateEntityError,
    EntityNotFoundError,
    InactiveUserError,
    InvalidInputError,
)

logger = logging.getLogger(__name__)

# Exception → HTTP status code mapping
STATUS_CODE_MAP: dict[type[AppException], int] = {
    EntityNotFoundError: 404,
    DuplicateEntityError: 409,
    AuthenticationError: 401,
    AuthorizationError: 403,
    InvalidInputError: 422,
    InactiveUserError: 403,
}


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        """Handle all custom application exceptions."""
        status_code = STATUS_CODE_MAP.get(type(exc), 500)
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "message": exc.message,
                    "detail": exc.detail,
                    "type": type(exc).__name__,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Catch-all handler for unexpected errors — never leak internal details."""
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Internal server error",
                    "detail": "An unexpected error occurred. Please try again later.",
                    "type": "InternalServerError",
                }
            },
        )
