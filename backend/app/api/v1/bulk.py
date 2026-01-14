"""Bulk operations API endpoints."""
from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import Field
from sqlalchemy import select, update, delete

from app.api.deps import CurrentUser, DbSession
from app.models.asset import Asset
from app.models.credential import Credential
from app.models.job import Job
from app.models.vulnerability import Vulnerability
from app.schemas.common import BaseSchema, MessageResponse

router = APIRouter()


class BulkEntityType(str, Enum):
    """Entity types for bulk operations."""

    ASSETS = "assets"
    VULNERABILITIES = "vulnerabilities"
    CREDENTIALS = "credentials"
    JOBS = "jobs"


class BulkAction(str, Enum):
    """Available bulk actions."""

    DELETE = "delete"
    UPDATE_STATUS = "update_status"
    UPDATE_TAGS = "update_tags"
    ASSIGN = "assign"
    ARCHIVE = "archive"
    EXPORT = "export"


class BulkOperationRequest(BaseSchema):
    """Request schema for bulk operations."""

    entity_type: BulkEntityType
    action: BulkAction
    ids: list[UUID] = Field(..., min_length=1, max_length=1000)
    data: dict[str, Any] | None = None  # Additional data for the action


class BulkOperationResult(BaseSchema):
    """Result of a bulk operation."""

    success: bool
    action: BulkAction
    entity_type: BulkEntityType
    total: int
    processed: int
    failed: int
    errors: list[dict[str, Any]] = []


@router.post("", response_model=BulkOperationResult)
async def bulk_operation(
    request: BulkOperationRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> BulkOperationResult:
    """
    Perform bulk operations on entities.

    Supports: delete, update_status, update_tags, assign, archive
    """
    total = len(request.ids)
    processed = 0
    failed = 0
    errors: list[dict[str, Any]] = []

    try:
        if request.action == BulkAction.DELETE:
            processed, failed, errors = await _bulk_delete(
                db, request.entity_type, request.ids
            )

        elif request.action == BulkAction.UPDATE_STATUS:
            if not request.data or "status" not in request.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Status value required for update_status action",
                )
            processed, failed, errors = await _bulk_update_status(
                db, request.entity_type, request.ids, request.data["status"]
            )

        elif request.action == BulkAction.UPDATE_TAGS:
            if not request.data or "tags" not in request.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tags required for update_tags action",
                )
            processed, failed, errors = await _bulk_update_tags(
                db,
                request.entity_type,
                request.ids,
                request.data["tags"],
                request.data.get("mode", "add"),  # add, remove, replace
            )

        elif request.action == BulkAction.ASSIGN:
            if not request.data or "user_id" not in request.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User ID required for assign action",
                )
            processed, failed, errors = await _bulk_assign(
                db, request.entity_type, request.ids, UUID(request.data["user_id"])
            )

        elif request.action == BulkAction.ARCHIVE:
            processed, failed, errors = await _bulk_archive(
                db, request.entity_type, request.ids
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported action: {request.action}",
            )

        await db.commit()

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk operation failed: {str(e)}",
        )

    return BulkOperationResult(
        success=failed == 0,
        action=request.action,
        entity_type=request.entity_type,
        total=total,
        processed=processed,
        failed=failed,
        errors=errors,
    )


async def _bulk_delete(
    db: DbSession,
    entity_type: BulkEntityType,
    ids: list[UUID],
) -> tuple[int, int, list[dict]]:
    """Delete multiple entities."""
    model = _get_model(entity_type)
    result = await db.execute(
        delete(model).where(model.id.in_(ids))
    )
    processed = result.rowcount
    failed = len(ids) - processed
    return processed, failed, []


async def _bulk_update_status(
    db: DbSession,
    entity_type: BulkEntityType,
    ids: list[UUID],
    new_status: str,
) -> tuple[int, int, list[dict]]:
    """Update status of multiple entities."""
    model = _get_model(entity_type)

    if not hasattr(model, "status"):
        return 0, len(ids), [{"error": f"{entity_type} does not have a status field"}]

    result = await db.execute(
        update(model).where(model.id.in_(ids)).values(status=new_status)
    )
    processed = result.rowcount
    failed = len(ids) - processed
    return processed, failed, []


async def _bulk_update_tags(
    db: DbSession,
    entity_type: BulkEntityType,
    ids: list[UUID],
    tags: list[str],
    mode: str,
) -> tuple[int, int, list[dict]]:
    """Update tags of multiple entities."""
    model = _get_model(entity_type)

    if not hasattr(model, "tags"):
        return 0, len(ids), [{"error": f"{entity_type} does not have tags"}]

    # Get entities
    result = await db.execute(select(model).where(model.id.in_(ids)))
    entities = result.scalars().all()

    processed = 0
    for entity in entities:
        if mode == "add":
            current_tags = set(entity.tags or [])
            entity.tags = list(current_tags | set(tags))
        elif mode == "remove":
            current_tags = set(entity.tags or [])
            entity.tags = list(current_tags - set(tags))
        elif mode == "replace":
            entity.tags = tags
        processed += 1

    failed = len(ids) - processed
    return processed, failed, []


async def _bulk_assign(
    db: DbSession,
    entity_type: BulkEntityType,
    ids: list[UUID],
    user_id: UUID,
) -> tuple[int, int, list[dict]]:
    """Assign multiple entities to a user."""
    model = _get_model(entity_type)

    if not hasattr(model, "assigned_to"):
        return 0, len(ids), [{"error": f"{entity_type} cannot be assigned"}]

    result = await db.execute(
        update(model).where(model.id.in_(ids)).values(assigned_to=user_id)
    )
    processed = result.rowcount
    failed = len(ids) - processed
    return processed, failed, []


async def _bulk_archive(
    db: DbSession,
    entity_type: BulkEntityType,
    ids: list[UUID],
) -> tuple[int, int, list[dict]]:
    """Archive multiple entities."""
    model = _get_model(entity_type)
    status_field = "status"

    if hasattr(model, status_field):
        result = await db.execute(
            update(model).where(model.id.in_(ids)).values(status="archived")
        )
        processed = result.rowcount
        failed = len(ids) - processed
        return processed, failed, []

    return 0, len(ids), [{"error": f"{entity_type} cannot be archived"}]


def _get_model(entity_type: BulkEntityType):
    """Get SQLAlchemy model for entity type."""
    models = {
        BulkEntityType.ASSETS: Asset,
        BulkEntityType.VULNERABILITIES: Vulnerability,
        BulkEntityType.CREDENTIALS: Credential,
        BulkEntityType.JOBS: Job,
    }
    return models[entity_type]


@router.post("/validate")
async def validate_bulk_operation(
    request: BulkOperationRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Validate a bulk operation before executing.

    Returns which entities exist and can be operated on.
    """
    model = _get_model(request.entity_type)

    # Check which IDs exist
    result = await db.execute(
        select(model.id).where(model.id.in_(request.ids))
    )
    existing_ids = {row[0] for row in result}

    valid_ids = [id for id in request.ids if id in existing_ids]
    invalid_ids = [id for id in request.ids if id not in existing_ids]

    return {
        "valid": True if not invalid_ids else False,
        "total": len(request.ids),
        "valid_count": len(valid_ids),
        "invalid_count": len(invalid_ids),
        "valid_ids": valid_ids,
        "invalid_ids": invalid_ids,
    }


@router.get("/supported-actions")
async def get_supported_actions(
    entity_type: BulkEntityType | None = None,
) -> dict:
    """Get supported bulk actions for each entity type."""
    actions = {
        BulkEntityType.ASSETS: [
            BulkAction.DELETE,
            BulkAction.UPDATE_STATUS,
            BulkAction.UPDATE_TAGS,
            BulkAction.ARCHIVE,
        ],
        BulkEntityType.VULNERABILITIES: [
            BulkAction.DELETE,
            BulkAction.UPDATE_STATUS,
            BulkAction.UPDATE_TAGS,
            BulkAction.ASSIGN,
            BulkAction.ARCHIVE,
        ],
        BulkEntityType.CREDENTIALS: [
            BulkAction.DELETE,
            BulkAction.ARCHIVE,
        ],
        BulkEntityType.JOBS: [
            BulkAction.DELETE,
        ],
    }

    if entity_type:
        return {
            "entity_type": entity_type,
            "actions": [a.value for a in actions.get(entity_type, [])],
        }

    return {
        entity.value: [a.value for a in acts]
        for entity, acts in actions.items()
    }
