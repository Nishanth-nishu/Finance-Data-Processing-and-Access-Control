"""
Custom exception classes for structured error handling.
Each exception maps to a specific HTTP status code via the global error handler.
"""


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, detail: str | None = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class EntityNotFoundError(AppException):
    """Raised when a requested entity does not exist. Maps to 404."""

    def __init__(self, entity_name: str, identifier: str | int):
        super().__init__(
            message=f"{entity_name} not found",
            detail=f"{entity_name} with identifier '{identifier}' does not exist.",
        )


class DuplicateEntityError(AppException):
    """Raised when attempting to create a duplicate entity. Maps to 409."""

    def __init__(self, entity_name: str, field: str, value: str):
        super().__init__(
            message=f"{entity_name} already exists",
            detail=f"A {entity_name} with {field} '{value}' already exists.",
        )


class AuthenticationError(AppException):
    """Raised when authentication fails. Maps to 401."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message=message)


class AuthorizationError(AppException):
    """Raised when authorization fails. Maps to 403."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message)


class InvalidInputError(AppException):
    """Raised when input validation fails. Maps to 422."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message=message, detail=detail)


class InactiveUserError(AppException):
    """Raised when an inactive user tries to perform an action. Maps to 403."""

    def __init__(self):
        super().__init__(
            message="Account is inactive",
            detail="Your account has been deactivated. Contact an administrator.",
        )
