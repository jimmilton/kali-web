"""Authentication API endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.rate_limiter import auth_rate_limit
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    hash_token,
    verify_password,
    verify_token,
    generate_mfa_secret,
    generate_mfa_qr_uri,
    generate_backup_codes,
    verify_mfa_code,
)
from app.config import settings
from app.models.user import PasswordResetToken, RefreshToken, User
from app.schemas.user import (
    LoginRequest,
    MFASetup,
    MFAVerify,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
    RefreshTokenRequest,
    RegisterRequest,
    Token,
    UserCreate,
    UserResponse,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limit)],
)
async def register(
    data: RegisterRequest,
    db: DbSession,
) -> User:
    """Register a new user."""
    # Check if user already exists
    result = await db.execute(
        select(User).where((User.email == data.email) | (User.username == data.username))
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        if existing_user.email == data.email:
            raise ConflictError("Email already registered")
        raise ConflictError("Username already taken")

    # Create new user
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


@router.post("/login", response_model=Token, dependencies=[Depends(auth_rate_limit)])
async def login(
    data: LoginRequest,
    db: DbSession,
) -> dict:
    """Authenticate user and return tokens."""
    # Find user by username or email
    result = await db.execute(
        select(User).where(
            (User.username == data.username) | (User.email == data.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise AuthenticationError("Invalid username or password")

    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    # Check MFA if enabled
    if user.mfa_enabled:
        if not data.mfa_code:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail="MFA code required",
            )
        if not verify_mfa_code(user.mfa_secret, data.mfa_code):
            raise AuthenticationError("Invalid MFA code")

    # Create tokens
    access_token = create_access_token(
        subject=user.id,
        additional_claims={"role": user.role},
    )
    refresh_token, token_hash, expires_at = create_refresh_token(subject=user.id)

    # Store refresh token
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(refresh_token_record)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 30 * 60,  # 30 minutes in seconds
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    data: RefreshTokenRequest,
    db: DbSession,
) -> dict:
    """Refresh access token using refresh token."""
    # Verify refresh token
    payload = verify_token(data.refresh_token, token_type="refresh")
    if not payload:
        raise AuthenticationError("Invalid or expired refresh token")

    user_id = payload.get("sub")
    token_hash = hash_token(data.refresh_token)

    # Find and validate refresh token in database
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow(),
        )
    )
    stored_token = result.scalar_one_or_none()

    if not stored_token:
        raise AuthenticationError("Refresh token not found or revoked")

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    # Revoke old refresh token
    stored_token.revoked = True

    # Create new tokens
    access_token = create_access_token(
        subject=user.id,
        additional_claims={"role": user.role},
    )
    new_refresh_token, new_token_hash, expires_at = create_refresh_token(subject=user.id)

    # Store new refresh token
    new_refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=new_token_hash,
        expires_at=expires_at,
    )
    db.add(new_refresh_token_record)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": 30 * 60,
    }


@router.post("/logout")
async def logout(
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Logout user and revoke all refresh tokens."""
    # Revoke all refresh tokens for this user
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked == False,
        )
    )
    tokens = result.scalars().all()

    for token in tokens:
        token.revoked = True

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
) -> User:
    """Get current user information."""
    return current_user


@router.post("/change-password")
async def change_password(
    data: PasswordChange,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Change user password."""
    # Verify current password
    if not verify_password(data.current_password, current_user.password_hash):
        raise AuthenticationError("Current password is incorrect")

    # Update password
    current_user.password_hash = get_password_hash(data.new_password)

    # Revoke all refresh tokens (force re-login)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked == False,
        )
    )
    tokens = result.scalars().all()
    for token in tokens:
        token.revoked = True

    return {"message": "Password changed successfully"}


@router.post("/mfa/setup", response_model=MFASetup)
async def setup_mfa(
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Setup MFA for the current user."""
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )

    # Generate MFA secret
    secret = generate_mfa_secret()
    current_user.mfa_secret = secret

    # Generate QR code URI
    qr_uri = generate_mfa_qr_uri(secret, current_user.email)

    # Generate backup codes
    backup_codes = generate_backup_codes()

    return {
        "secret": secret,
        "qr_code": qr_uri,
        "backup_codes": backup_codes,
    }


@router.post("/mfa/enable")
async def enable_mfa(
    data: MFAVerify,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Enable MFA after verifying the code."""
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup not initiated",
        )

    if not verify_mfa_code(current_user.mfa_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )

    current_user.mfa_enabled = True

    return {"message": "MFA enabled successfully"}


@router.post("/mfa/disable")
async def disable_mfa(
    data: MFAVerify,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Disable MFA for the current user."""
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )

    if not verify_mfa_code(current_user.mfa_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )

    current_user.mfa_enabled = False
    current_user.mfa_secret = None

    return {"message": "MFA disabled successfully"}


@router.post(
    "/password-reset/request",
    response_model=PasswordResetResponse,
    dependencies=[Depends(auth_rate_limit)],
)
async def request_password_reset(
    data: PasswordResetRequest,
    db: DbSession,
) -> dict:
    """Request a password reset token."""
    import secrets
    from datetime import timedelta, timezone

    from app.core.security import hash_token

    # Find user by email
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    response = {
        "message": "If an account exists with that email, a reset link has been sent.",
    }

    if user and user.is_active:
        # Generate reset token
        token = secrets.token_urlsafe(32)
        token_hash = hash_token(token)

        # Token expires in 1 hour
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Invalidate any existing reset tokens for this user
        existing_tokens = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used == False,
            )
        )
        for existing_token in existing_tokens.scalars().all():
            existing_token.used = True

        # Create new reset token
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_token)
        await db.flush()

        # In production, send email with reset link
        # For now, we'll return the token in debug mode
        if settings.debug:
            response["reset_token"] = token

        # TODO: Send email with reset link
        # reset_link = f"{settings.frontend_url}/reset-password?token={token}"
        # await send_password_reset_email(user.email, reset_link)

    return response


@router.post(
    "/password-reset/confirm",
    dependencies=[Depends(auth_rate_limit)],
)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    db: DbSession,
) -> dict:
    """Confirm password reset with token."""
    from datetime import timezone

    from app.core.security import hash_token

    token_hash = hash_token(data.token)

    # Find valid reset token
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        )
    )
    reset_token = result.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Get user
    result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    # Update password
    from app.core.security import get_password_hash

    user.password_hash = get_password_hash(data.new_password)

    # Mark token as used
    reset_token.used = True

    # Revoke all refresh tokens (force re-login)
    existing_tokens = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked == False,
        )
    )
    for token in existing_tokens.scalars().all():
        token.revoked = True

    return {"message": "Password has been reset successfully"}
