"""Permission system for role-based access control."""

from enum import Enum
from functools import wraps
from typing import Callable, List, Optional, Set
from uuid import UUID

from fastapi import HTTPException, status

from app.models.user import UserRole
from app.models.project import ProjectRole


class Permission(str, Enum):
    """Permission enumeration."""

    # User permissions
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_MANAGE = "user:manage"

    # Project permissions
    PROJECT_READ = "project:read"
    PROJECT_CREATE = "project:create"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"
    PROJECT_MANAGE = "project:manage"

    # Asset permissions
    ASSET_READ = "asset:read"
    ASSET_CREATE = "asset:create"
    ASSET_UPDATE = "asset:update"
    ASSET_DELETE = "asset:delete"
    ASSET_IMPORT = "asset:import"

    # Job permissions
    JOB_READ = "job:read"
    JOB_CREATE = "job:create"
    JOB_CANCEL = "job:cancel"
    JOB_DELETE = "job:delete"

    # Vulnerability permissions
    VULN_READ = "vuln:read"
    VULN_CREATE = "vuln:create"
    VULN_UPDATE = "vuln:update"
    VULN_DELETE = "vuln:delete"

    # Credential permissions
    CREDENTIAL_READ = "credential:read"
    CREDENTIAL_CREATE = "credential:create"
    CREDENTIAL_UPDATE = "credential:update"
    CREDENTIAL_DELETE = "credential:delete"
    CREDENTIAL_VIEW_SECRET = "credential:view_secret"

    # Workflow permissions
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_CREATE = "workflow:create"
    WORKFLOW_UPDATE = "workflow:update"
    WORKFLOW_DELETE = "workflow:delete"
    WORKFLOW_EXECUTE = "workflow:execute"

    # Report permissions
    REPORT_READ = "report:read"
    REPORT_CREATE = "report:create"
    REPORT_UPDATE = "report:update"
    REPORT_DELETE = "report:delete"
    REPORT_GENERATE = "report:generate"

    # Integration permissions
    INTEGRATION_READ = "integration:read"
    INTEGRATION_MANAGE = "integration:manage"

    # Admin permissions
    ADMIN_AUDIT_LOG = "admin:audit_log"
    ADMIN_SETTINGS = "admin:settings"
    ADMIN_BACKUP = "admin:backup"


# Role to permissions mapping (system-wide roles)
ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
    UserRole.ADMIN: set(Permission),  # Admin has all permissions
    UserRole.MANAGER: {
        Permission.USER_READ,
        Permission.PROJECT_READ,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_MANAGE,
        Permission.ASSET_READ,
        Permission.ASSET_CREATE,
        Permission.ASSET_UPDATE,
        Permission.ASSET_DELETE,
        Permission.ASSET_IMPORT,
        Permission.JOB_READ,
        Permission.JOB_CREATE,
        Permission.JOB_CANCEL,
        Permission.VULN_READ,
        Permission.VULN_CREATE,
        Permission.VULN_UPDATE,
        Permission.VULN_DELETE,
        Permission.CREDENTIAL_READ,
        Permission.CREDENTIAL_CREATE,
        Permission.CREDENTIAL_UPDATE,
        Permission.CREDENTIAL_DELETE,
        Permission.CREDENTIAL_VIEW_SECRET,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_UPDATE,
        Permission.WORKFLOW_DELETE,
        Permission.WORKFLOW_EXECUTE,
        Permission.REPORT_READ,
        Permission.REPORT_CREATE,
        Permission.REPORT_UPDATE,
        Permission.REPORT_DELETE,
        Permission.REPORT_GENERATE,
        Permission.INTEGRATION_READ,
        Permission.INTEGRATION_MANAGE,
    },
    UserRole.OPERATOR: {
        Permission.PROJECT_READ,
        Permission.PROJECT_CREATE,
        Permission.ASSET_READ,
        Permission.ASSET_CREATE,
        Permission.ASSET_UPDATE,
        Permission.ASSET_IMPORT,
        Permission.JOB_READ,
        Permission.JOB_CREATE,
        Permission.JOB_CANCEL,
        Permission.VULN_READ,
        Permission.VULN_CREATE,
        Permission.VULN_UPDATE,
        Permission.CREDENTIAL_READ,
        Permission.CREDENTIAL_CREATE,
        Permission.CREDENTIAL_UPDATE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_EXECUTE,
        Permission.REPORT_READ,
        Permission.REPORT_CREATE,
        Permission.REPORT_GENERATE,
    },
    UserRole.VIEWER: {
        Permission.PROJECT_READ,
        Permission.ASSET_READ,
        Permission.JOB_READ,
        Permission.VULN_READ,
        Permission.CREDENTIAL_READ,
        Permission.WORKFLOW_READ,
        Permission.REPORT_READ,
    },
}

# Project role to permissions mapping (within a project)
PROJECT_ROLE_PERMISSIONS: dict[ProjectRole, Set[Permission]] = {
    ProjectRole.OWNER: {
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_MANAGE,
        Permission.ASSET_READ,
        Permission.ASSET_CREATE,
        Permission.ASSET_UPDATE,
        Permission.ASSET_DELETE,
        Permission.ASSET_IMPORT,
        Permission.JOB_READ,
        Permission.JOB_CREATE,
        Permission.JOB_CANCEL,
        Permission.JOB_DELETE,
        Permission.VULN_READ,
        Permission.VULN_CREATE,
        Permission.VULN_UPDATE,
        Permission.VULN_DELETE,
        Permission.CREDENTIAL_READ,
        Permission.CREDENTIAL_CREATE,
        Permission.CREDENTIAL_UPDATE,
        Permission.CREDENTIAL_DELETE,
        Permission.CREDENTIAL_VIEW_SECRET,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_UPDATE,
        Permission.WORKFLOW_DELETE,
        Permission.WORKFLOW_EXECUTE,
        Permission.REPORT_READ,
        Permission.REPORT_CREATE,
        Permission.REPORT_UPDATE,
        Permission.REPORT_DELETE,
        Permission.REPORT_GENERATE,
    },
    ProjectRole.MANAGER: {
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_MANAGE,
        Permission.ASSET_READ,
        Permission.ASSET_CREATE,
        Permission.ASSET_UPDATE,
        Permission.ASSET_DELETE,
        Permission.ASSET_IMPORT,
        Permission.JOB_READ,
        Permission.JOB_CREATE,
        Permission.JOB_CANCEL,
        Permission.VULN_READ,
        Permission.VULN_CREATE,
        Permission.VULN_UPDATE,
        Permission.VULN_DELETE,
        Permission.CREDENTIAL_READ,
        Permission.CREDENTIAL_CREATE,
        Permission.CREDENTIAL_UPDATE,
        Permission.CREDENTIAL_DELETE,
        Permission.CREDENTIAL_VIEW_SECRET,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_UPDATE,
        Permission.WORKFLOW_DELETE,
        Permission.WORKFLOW_EXECUTE,
        Permission.REPORT_READ,
        Permission.REPORT_CREATE,
        Permission.REPORT_UPDATE,
        Permission.REPORT_DELETE,
        Permission.REPORT_GENERATE,
    },
    ProjectRole.MEMBER: {
        Permission.PROJECT_READ,
        Permission.ASSET_READ,
        Permission.ASSET_CREATE,
        Permission.ASSET_UPDATE,
        Permission.ASSET_IMPORT,
        Permission.JOB_READ,
        Permission.JOB_CREATE,
        Permission.JOB_CANCEL,
        Permission.VULN_READ,
        Permission.VULN_CREATE,
        Permission.VULN_UPDATE,
        Permission.CREDENTIAL_READ,
        Permission.CREDENTIAL_CREATE,
        Permission.CREDENTIAL_UPDATE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_EXECUTE,
        Permission.REPORT_READ,
        Permission.REPORT_CREATE,
        Permission.REPORT_GENERATE,
    },
    ProjectRole.VIEWER: {
        Permission.PROJECT_READ,
        Permission.ASSET_READ,
        Permission.JOB_READ,
        Permission.VULN_READ,
        Permission.CREDENTIAL_READ,
        Permission.WORKFLOW_READ,
        Permission.REPORT_READ,
    },
}


def get_role_permissions(role: UserRole) -> Set[Permission]:
    """Get permissions for a system role."""
    return ROLE_PERMISSIONS.get(role, set())


def get_project_role_permissions(role: ProjectRole) -> Set[Permission]:
    """Get permissions for a project role."""
    return PROJECT_ROLE_PERMISSIONS.get(role, set())


def check_permission(
    user_role: UserRole,
    permission: Permission,
    project_role: Optional[ProjectRole] = None,
) -> bool:
    """
    Check if a user has a specific permission.

    Args:
        user_role: The user's system role
        permission: The permission to check
        project_role: Optional project-specific role

    Returns:
        True if the user has the permission
    """
    # Admin always has all permissions
    if user_role == UserRole.ADMIN:
        return True

    # Check system role permissions
    if permission in get_role_permissions(user_role):
        return True

    # Check project role permissions if provided
    if project_role and permission in get_project_role_permissions(project_role):
        return True

    return False


def require_permission(*permissions: Permission) -> Callable:
    """
    Decorator to require specific permissions.

    Usage:
        @require_permission(Permission.PROJECT_CREATE)
        async def create_project(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This is a placeholder - actual implementation
            # would get the current user from the request context
            # and check their permissions
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class PermissionChecker:
    """Permission checker for dependency injection."""

    def __init__(self, *required_permissions: Permission):
        self.required_permissions = required_permissions

    def __call__(
        self,
        user_role: UserRole,
        project_role: Optional[ProjectRole] = None,
    ) -> bool:
        """Check if all required permissions are satisfied."""
        for permission in self.required_permissions:
            if not check_permission(user_role, permission, project_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value}",
                )
        return True
