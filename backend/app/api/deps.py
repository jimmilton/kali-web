"""API dependencies for authentication and authorization."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorizationError, NotFoundError
from app.core.permissions import Permission, check_permission
from app.core.security import verify_token
from app.db.session import get_db
from app.models.project import Project, ProjectMember, ProjectRole
from app.models.user import User, UserRole

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get the current authenticated user."""
    if not credentials:
        raise AuthenticationError("Missing authentication token")

    token = credentials.credentials
    payload = verify_token(token, token_type="access")

    if not payload:
        raise AuthenticationError("Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token payload")

    # Get user from database
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("User not found")

    if not user.is_active:
        raise AuthenticationError("User is inactive")

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise AuthenticationError("Inactive user")
    return current_user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get the current user if they are a superuser."""
    if not current_user.is_superuser:
        raise AuthorizationError("Superuser access required")
    return current_user


async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[User]:
    """Get the current user if authenticated, None otherwise."""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except AuthenticationError:
        return None


class PermissionDependency:
    """Dependency class for checking permissions."""

    def __init__(self, *permissions: Permission):
        self.permissions = permissions

    async def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Check if the user has the required permissions."""
        user_role = UserRole(current_user.role)

        for permission in self.permissions:
            if not check_permission(user_role, permission):
                raise AuthorizationError(f"Permission denied: {permission.value}")

        return current_user


class ProjectPermissionDependency:
    """Dependency class for checking project-specific permissions."""

    def __init__(self, *permissions: Permission):
        self.permissions = permissions

    async def __call__(
        self,
        project_id: UUID,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> tuple[User, Project, Optional[ProjectRole]]:
        """Check if the user has the required permissions for the project."""
        # Get the project
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()

        if not project:
            raise NotFoundError("Project", str(project_id))

        user_role = UserRole(current_user.role)

        # Admin has access to everything
        if user_role == UserRole.ADMIN:
            return current_user, project, ProjectRole.OWNER

        # Get the user's project membership
        result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user.id,
            )
        )
        membership = result.scalar_one_or_none()

        if not membership:
            # Check if user is the creator
            if project.created_by == current_user.id:
                project_role = ProjectRole.OWNER
            else:
                raise AuthorizationError("Not a member of this project")
        else:
            project_role = ProjectRole(membership.role)

        # Check permissions
        for permission in self.permissions:
            if not check_permission(user_role, permission, project_role):
                raise AuthorizationError(f"Permission denied: {permission.value}")

        return current_user, project, project_role


# Common query parameters
class PaginationParams:
    """Pagination query parameters."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size


class SortParams:
    """Sort query parameters."""

    def __init__(
        self,
        sort_by: Optional[str] = Query(None, description="Field to sort by"),
        sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    ):
        self.sort_by = sort_by
        self.sort_order = sort_order


# Type aliases for common dependencies
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PaginationParams, Depends()]
Sort = Annotated[SortParams, Depends()]
