"""Users API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperuser, CurrentUser, DbSession, Pagination, PermissionDependency
from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import Permission
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    current_user: CurrentSuperuser,
    db: DbSession,
    pagination: Pagination,
    search: str = None,
) -> dict:
    """List all users (admin only)."""
    query = select(User)

    if search:
        query = query.where(
            (User.username.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%"))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results
    query = query.offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    return {
        "items": users,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": (total + pagination.page_size - 1) // pagination.page_size,
    }


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> User:
    """Create a new user (admin only)."""
    # Check for existing user
    result = await db.execute(
        select(User).where((User.email == data.email) | (User.username == data.username))
    )
    if result.scalar_one_or_none():
        raise ConflictError("User with this email or username already exists")

    # Handle both enum instances and string values (Pydantic v2 with use_enum_values)
    user_role = data.role.value if hasattr(data.role, 'value') else data.role

    user = User(
        email=data.email,
        username=data.username,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        role=user_role,
    )

    db.add(user)
    await db.flush()
    await db.refresh(user)

    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> User:
    """Get a user by ID."""
    # Users can view their own profile, admins can view any
    if user_id != current_user.id and not current_user.is_superuser:
        raise NotFoundError("User", str(user_id))

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundError("User", str(user_id))

    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> User:
    """Update a user."""
    # Users can update their own profile, admins can update any
    if user_id != current_user.id and not current_user.is_superuser:
        raise NotFoundError("User", str(user_id))

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundError("User", str(user_id))

    # Only admins can change roles
    if data.role and not current_user.is_superuser:
        data.role = None

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)

    await db.flush()
    await db.refresh(user)

    return user


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: UUID,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> dict:
    """Delete a user (admin only)."""
    if user_id == current_user.id:
        raise ConflictError("Cannot delete your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundError("User", str(user_id))

    await db.delete(user)

    return {"message": "User deleted successfully", "success": True}
