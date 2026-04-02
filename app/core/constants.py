"""
Enums and constants for the finance dashboard system.
Uses Python enums for type safety and data-driven permission matrix
following the Open/Closed Principle.
"""

from enum import Enum
from typing import FrozenSet


class UserRole(str, Enum):
    """User roles within the finance dashboard system."""
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"


class RecordType(str, Enum):
    """Financial record types."""
    INCOME = "income"
    EXPENSE = "expense"


class Permission(str, Enum):
    """Granular permissions for RBAC enforcement."""
    # Record permissions
    RECORD_VIEW = "record:view"
    RECORD_CREATE = "record:create"
    RECORD_UPDATE = "record:update"
    RECORD_DELETE = "record:delete"

    # Dashboard permissions
    DASHBOARD_VIEW_RECENT = "dashboard:view_recent"
    DASHBOARD_VIEW_SUMMARY = "dashboard:view_summary"
    DASHBOARD_VIEW_TRENDS = "dashboard:view_trends"
    DASHBOARD_VIEW_CATEGORIES = "dashboard:view_categories"

    # User management permissions
    USER_VIEW_SELF = "user:view_self"
    USER_VIEW_ALL = "user:view_all"
    USER_MANAGE = "user:manage"
    USER_ASSIGN_ROLE = "user:assign_role"


# Data-driven permission matrix — adding new roles/permissions
# requires no code changes to enforcement logic (Open/Closed Principle)
ROLE_PERMISSIONS: dict[UserRole, FrozenSet[Permission]] = {
    UserRole.VIEWER: frozenset({
        Permission.RECORD_VIEW,
        Permission.DASHBOARD_VIEW_RECENT,
        Permission.USER_VIEW_SELF,
    }),
    UserRole.ANALYST: frozenset({
        Permission.RECORD_VIEW,
        Permission.DASHBOARD_VIEW_RECENT,
        Permission.DASHBOARD_VIEW_SUMMARY,
        Permission.DASHBOARD_VIEW_TRENDS,
        Permission.DASHBOARD_VIEW_CATEGORIES,
        Permission.USER_VIEW_SELF,
    }),
    UserRole.ADMIN: frozenset({
        Permission.RECORD_VIEW,
        Permission.RECORD_CREATE,
        Permission.RECORD_UPDATE,
        Permission.RECORD_DELETE,
        Permission.DASHBOARD_VIEW_RECENT,
        Permission.DASHBOARD_VIEW_SUMMARY,
        Permission.DASHBOARD_VIEW_TRENDS,
        Permission.DASHBOARD_VIEW_CATEGORIES,
        Permission.USER_VIEW_SELF,
        Permission.USER_VIEW_ALL,
        Permission.USER_MANAGE,
        Permission.USER_ASSIGN_ROLE,
    }),
}


def has_permission(role: UserRole, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


# Default pagination settings
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Financial record categories (extensible)
DEFAULT_CATEGORIES = [
    "salary",
    "freelance",
    "investment",
    "rental",
    "food",
    "transport",
    "utilities",
    "entertainment",
    "healthcare",
    "education",
    "shopping",
    "other",
]
