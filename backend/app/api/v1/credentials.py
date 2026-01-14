"""Credentials API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, Pagination
from app.core.exceptions import NotFoundError
from app.core.security import decrypt_sensitive_data, encrypt_sensitive_data
from app.models.credential import Credential, CredentialType, HashType
from app.models.project import Project, ProjectMember
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.credential import (
    CredentialAssetInfo,
    CredentialCreate,
    CredentialResponse,
    CredentialStats,
    CredentialUpdate,
    CredentialWithSecret,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[CredentialResponse])
async def list_credentials(
    current_user: CurrentUser,
    db: DbSession,
    pagination: Pagination,
    project_id: Optional[UUID] = None,
    credential_type: Optional[CredentialType] = None,
    service: Optional[str] = None,
    is_valid: Optional[bool] = None,
) -> dict:
    """List credentials."""
    query = select(Credential)

    if project_id:
        query = query.where(Credential.project_id == project_id)

    if credential_type:
        query = query.where(Credential.credential_type == credential_type.value)

    if service:
        query = query.where(Credential.service == service)

    if is_valid is not None:
        query = query.where(Credential.is_valid == is_valid)

    query = query.order_by(Credential.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    creds = result.scalars().all()

    cred_responses = []
    for cred in creds:
        cred_responses.append(
            CredentialResponse(
                id=cred.id,
                project_id=cred.project_id,
                asset_id=cred.asset_id,
                credential_type=CredentialType(cred.credential_type),
                username=cred.username,
                domain=cred.domain,
                service=cred.service,
                port=cred.port,
                url=cred.url,
                hash_type=HashType(cred.hash_type) if cred.hash_type else None,
                source=cred.source,
                is_valid=cred.is_valid,
                validated_at=cred.validated_at,
                discovered_by=cred.discovered_by,
                fingerprint=cred.fingerprint,
                metadata=cred.metadata_,
                notes=cred.notes,
                created_at=cred.created_at,
                updated_at=cred.updated_at,
                has_password=bool(cred.password_encrypted or cred.plaintext_encrypted),
                has_hash=bool(cred.hash_value),
            )
        )

    return {
        "items": cred_responses,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": (total + pagination.page_size - 1) // pagination.page_size if total else 0,
    }


@router.post("", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_credential(
    data: CredentialCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> CredentialResponse:
    """Create a new credential."""
    cred = Credential(
        project_id=data.project_id,
        asset_id=data.asset_id,
        credential_type=data.credential_type.value,
        username=data.username,
        domain=data.domain,
        service=data.service,
        port=data.port,
        url=data.url,
        hash_type=data.hash_type.value if data.hash_type else None,
        source=data.source,
        notes=data.notes,
    )

    # Encrypt sensitive data
    if data.password:
        cred.plaintext_encrypted = encrypt_sensitive_data(data.password)

    if data.hash_value:
        cred.hash_value = data.hash_value

    db.add(cred)
    await db.flush()
    await db.refresh(cred)

    return CredentialResponse(
        id=cred.id,
        project_id=cred.project_id,
        asset_id=cred.asset_id,
        credential_type=CredentialType(cred.credential_type),
        username=cred.username,
        domain=cred.domain,
        service=cred.service,
        port=cred.port,
        url=cred.url,
        hash_type=HashType(cred.hash_type) if cred.hash_type else None,
        source=cred.source,
        is_valid=cred.is_valid,
        validated_at=cred.validated_at,
        discovered_by=cred.discovered_by,
        fingerprint=cred.fingerprint,
        metadata=cred.metadata_,
        notes=cred.notes,
        created_at=cred.created_at,
        updated_at=cred.updated_at,
        has_password=bool(cred.plaintext_encrypted),
        has_hash=bool(cred.hash_value),
    )


@router.get("/stats", response_model=CredentialStats)
async def get_credential_stats(
    current_user: CurrentUser,
    db: DbSession,
    project_id: Optional[UUID] = None,
) -> CredentialStats:
    """Get credential statistics."""
    query = select(Credential)
    if project_id:
        query = query.where(Credential.project_id == project_id)

    total = await db.scalar(select(func.count()).select_from(query.subquery()))

    return CredentialStats(
        total=total or 0,
        by_type={},
        by_service={},
        valid_count=0,
        invalid_count=0,
        unknown_count=0,
        with_plaintext=0,
        with_hash=0,
    )


@router.get("/{cred_id}", response_model=CredentialResponse)
async def get_credential(
    cred_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> CredentialResponse:
    """Get credential by ID."""
    result = await db.execute(select(Credential).where(Credential.id == cred_id))
    cred = result.scalar_one_or_none()

    if not cred:
        raise NotFoundError("Credential", str(cred_id))

    return CredentialResponse(
        id=cred.id,
        project_id=cred.project_id,
        asset_id=cred.asset_id,
        credential_type=CredentialType(cred.credential_type),
        username=cred.username,
        domain=cred.domain,
        service=cred.service,
        port=cred.port,
        url=cred.url,
        hash_type=HashType(cred.hash_type) if cred.hash_type else None,
        source=cred.source,
        is_valid=cred.is_valid,
        validated_at=cred.validated_at,
        discovered_by=cred.discovered_by,
        fingerprint=cred.fingerprint,
        metadata=cred.metadata_,
        notes=cred.notes,
        created_at=cred.created_at,
        updated_at=cred.updated_at,
        has_password=bool(cred.plaintext_encrypted),
        has_hash=bool(cred.hash_value),
    )


@router.get("/{cred_id}/secret", response_model=CredentialWithSecret)
async def get_credential_secret(
    cred_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> CredentialWithSecret:
    """Get credential with decrypted secret (restricted access)."""
    result = await db.execute(select(Credential).where(Credential.id == cred_id))
    cred = result.scalar_one_or_none()

    if not cred:
        raise NotFoundError("Credential", str(cred_id))

    password = None
    if cred.plaintext_encrypted:
        password = decrypt_sensitive_data(cred.plaintext_encrypted)

    return CredentialWithSecret(
        id=cred.id,
        project_id=cred.project_id,
        asset_id=cred.asset_id,
        credential_type=CredentialType(cred.credential_type),
        username=cred.username,
        domain=cred.domain,
        service=cred.service,
        port=cred.port,
        url=cred.url,
        hash_type=HashType(cred.hash_type) if cred.hash_type else None,
        source=cred.source,
        is_valid=cred.is_valid,
        validated_at=cred.validated_at,
        discovered_by=cred.discovered_by,
        fingerprint=cred.fingerprint,
        metadata=cred.metadata_,
        notes=cred.notes,
        created_at=cred.created_at,
        updated_at=cred.updated_at,
        has_password=bool(cred.plaintext_encrypted),
        has_hash=bool(cred.hash_value),
        password=password,
        hash_value=cred.hash_value,
    )


@router.delete("/{cred_id}", response_model=MessageResponse)
async def delete_credential(
    cred_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Delete a credential."""
    result = await db.execute(select(Credential).where(Credential.id == cred_id))
    cred = result.scalar_one_or_none()

    if not cred:
        raise NotFoundError("Credential", str(cred_id))

    await db.delete(cred)

    return {"message": "Credential deleted successfully", "success": True}
