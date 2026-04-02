"""
Authentication service — handles registration, login, and token refresh.
Business logic is framework-agnostic (no HTTP concepts).
"""

from app.core.constants import UserRole, UserStatus
from app.core.exceptions import (
    AuthenticationError,
    DuplicateEntityError,
    InactiveUserError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domain.models.user import User
from app.repositories.user_repository import UserRepository


class AuthService:
    """Orchestrates authentication workflows."""

    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo

    async def register(
        self,
        email: str,
        username: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        """
        Register a new user.

        Raises:
            DuplicateEntityError: If email or username already exists.
        """
        # Check for duplicate email
        existing = await self._user_repo.get_by_email(email)
        if existing:
            raise DuplicateEntityError("User", "email", email)

        # Check for duplicate username
        existing = await self._user_repo.get_by_username(username)
        if existing:
            raise DuplicateEntityError("User", "username", username)

        # Create user with hashed password
        user = User(
            email=email,
            username=username,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=UserRole.VIEWER,  # Default role
            status=UserStatus.ACTIVE,
        )

        return await self._user_repo.create(user)

    async def login(self, email: str, password: str) -> dict:
        """
        Authenticate a user and return tokens.

        Returns:
            Dict with access_token, refresh_token, and token_type.

        Raises:
            AuthenticationError: If credentials are invalid.
            InactiveUserError: If user account is inactive.
        """
        user = await self._user_repo.get_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if user.status == UserStatus.INACTIVE:
            raise InactiveUserError()

        return {
            "access_token": create_access_token(str(user.id), user.role.value),
            "refresh_token": create_refresh_token(str(user.id)),
            "token_type": "bearer",
        }

    async def refresh_token(self, refresh_token: str) -> dict:
        """
        Generate a new access token from a valid refresh token.

        Returns:
            Dict with new access_token and token_type.

        Raises:
            AuthenticationError: If refresh token is invalid.
            InactiveUserError: If user account is inactive.
        """
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type: expected refresh token")

        user = await self._user_repo.get_by_id(int(payload["sub"]))
        if not user:
            raise AuthenticationError("User not found")

        if user.status == UserStatus.INACTIVE:
            raise InactiveUserError()

        return {
            "access_token": create_access_token(str(user.id), user.role.value),
            "token_type": "bearer",
        }
