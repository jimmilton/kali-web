"""Assets API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, Pagination
from app.core.exceptions import ConflictError, NotFoundError
from app.models.asset import Asset, AssetRelation, AssetStatus, AssetType
from app.models.credential import Credential
from app.models.project import Project, ProjectMember
from app.models.vulnerability import Vulnerability
from app.schemas.asset import (
    AssetCreate,
    AssetFilter,
    AssetGraph,
    AssetImport,
    AssetImportResult,
    AssetRelationCreate,
    AssetRelationResponse,
    AssetResponse,
    AssetUpdate,
)
from app.schemas.common import MessageResponse, PaginatedResponse

router = APIRouter()


async def check_project_access(db: AsyncSession, project_id: UUID, user_id: UUID, is_superuser: bool) -> Project:
    """Check if user has access to project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise NotFoundError("Project", str(project_id))

    if not is_superuser:
        result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        if not result.scalar_one_or_none() and project.created_by != user_id:
            raise NotFoundError("Project", str(project_id))

    return project


@router.get("", response_model=PaginatedResponse[AssetResponse])
async def list_assets(
    current_user: CurrentUser,
    db: DbSession,
    pagination: Pagination,
    project_id: UUID = Query(...),
    asset_type: Optional[AssetType] = None,
    status: Optional[AssetStatus] = None,
    search: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
) -> dict:
    """List assets in a project."""
    await check_project_access(db, project_id, current_user.id, current_user.is_superuser)

    query = select(Asset).where(Asset.project_id == project_id)

    if asset_type:
        # Handle both enum instances and string values
        type_value = asset_type.value if hasattr(asset_type, 'value') else asset_type
        query = query.where(Asset.type == type_value)

    if status:
        # Handle both enum instances and string values
        status_value = status.value if hasattr(status, 'value') else status
        query = query.where(Asset.status == status_value)

    if search:
        query = query.where(Asset.value.ilike(f"%{search}%"))

    if tags:
        query = query.where(Asset.tags.overlap(tags))

    query = query.order_by(Asset.created_at.desc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Get paginated results
    query = query.offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    assets = result.scalars().all()

    # Get vulnerability and credential counts
    asset_responses = []
    for asset in assets:
        vuln_count = await db.scalar(
            select(func.count()).select_from(Vulnerability).where(Vulnerability.asset_id == asset.id)
        )
        cred_count = await db.scalar(
            select(func.count()).select_from(Credential).where(Credential.asset_id == asset.id)
        )

        asset_responses.append(
            AssetResponse(
                id=asset.id,
                project_id=asset.project_id,
                type=AssetType(asset.type),
                value=asset.value,
                metadata=asset.metadata_,
                tags=asset.tags,
                status=AssetStatus(asset.status),
                risk_score=asset.risk_score,
                discovered_by=asset.discovered_by,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
                vulnerability_count=vuln_count or 0,
                credential_count=cred_count or 0,
            )
        )

    return {
        "items": asset_responses,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": (total + pagination.page_size - 1) // pagination.page_size if total else 0,
    }


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    data: AssetCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> AssetResponse:
    """Create a new asset."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        await check_project_access(db, data.project_id, current_user.id, current_user.is_superuser)

        # Handle both enum instances and string values (Pydantic v2 with use_enum_values)
        asset_type = data.type.value if hasattr(data.type, 'value') else data.type
        asset_status = data.status.value if hasattr(data.status, 'value') else data.status

        # Check for duplicate
        result = await db.execute(
            select(Asset).where(
                Asset.project_id == data.project_id,
                Asset.type == asset_type,
                Asset.value == data.value,
            )
        )
        if result.scalar_one_or_none():
            raise ConflictError("Asset with this type and value already exists")

        # Ensure metadata and tags have proper defaults
        metadata = data.metadata_ if data.metadata_ is not None else {}
        tags = data.tags if data.tags is not None else []

        asset = Asset(
            project_id=data.project_id,
            type=asset_type,
            value=data.value,
            metadata_=metadata,
            tags=tags,
            status=asset_status,
        )

        db.add(asset)
        await db.flush()
        await db.refresh(asset)

        return AssetResponse(
            id=asset.id,
            project_id=asset.project_id,
            type=AssetType(asset.type),
            value=asset.value,
            metadata=asset.metadata_,
            tags=asset.tags,
            status=AssetStatus(asset.status),
            risk_score=asset.risk_score,
            discovered_by=asset.discovered_by,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
        )
    except ConflictError:
        raise
    except Exception as e:
        logger.error(f"Error creating asset: {e}", exc_info=True)
        raise


# =============================================================================
# SPECIFIC ROUTES - Must come before /{asset_id} parametric routes
# =============================================================================

@router.get("/graph", response_model=AssetGraph)
async def get_asset_graph(
    current_user: CurrentUser,
    db: DbSession,
    project_id: UUID = Query(...),
    root_asset_id: UUID | None = None,
    depth: int = Query(3, ge=1, le=10),
) -> AssetGraph:
    """Get asset relationship graph for visualization."""
    await check_project_access(db, project_id, current_user.id, current_user.is_superuser)

    # Get all assets for the project
    assets_query = select(Asset).where(Asset.project_id == project_id)
    assets_result = await db.execute(assets_query)
    assets = assets_result.scalars().all()

    # Get all relations between these assets
    asset_ids = [a.id for a in assets]
    relations_query = select(AssetRelation).where(
        AssetRelation.parent_id.in_(asset_ids),
        AssetRelation.child_id.in_(asset_ids),
    )
    relations_result = await db.execute(relations_query)
    relations = relations_result.scalars().all()

    # Build graph nodes and edges
    type_colors = {
        "host": "#22c55e",      # green
        "domain": "#3b82f6",    # blue
        "subdomain": "#8b5cf6", # purple
        "url": "#f97316",       # orange
        "service": "#06b6d4",   # cyan
        "network": "#eab308",   # yellow
        "endpoint": "#ec4899",  # pink
        "certificate": "#6366f1", # indigo
        "technology": "#14b8a6", # teal
    }

    nodes = []
    for asset in assets:
        nodes.append({
            "id": str(asset.id),
            "type": "asset",
            "data": {
                "label": asset.value,
                "asset_type": asset.type,
                "status": asset.status,
                "risk_score": asset.risk_score,
                "metadata": asset.metadata_,
            },
            "position": {"x": 0, "y": 0},  # Will be calculated by frontend layout
            "style": {
                "background": type_colors.get(asset.type, "#888"),
            },
        })

    edges = []
    for relation in relations:
        edges.append({
            "id": f"{relation.parent_id}-{relation.child_id}",
            "source": str(relation.parent_id),
            "target": str(relation.child_id),
            "label": relation.relation_type,
            "animated": False,
        })

    return AssetGraph(nodes=nodes, edges=edges)


@router.post("/import", response_model=AssetImportResult)
async def import_assets(
    data: AssetImport,
    project_id: UUID = Query(...),
    current_user: CurrentUser = None,
    db: DbSession = None,
) -> AssetImportResult:
    """Bulk import assets."""
    await check_project_access(db, project_id, current_user.id, current_user.is_superuser)

    imported = 0
    skipped = 0
    errors = []

    for item in data.assets:
        try:
            # Handle both enum instances and string values (Pydantic v2 with use_enum_values)
            item_type = item.type.value if hasattr(item.type, 'value') else item.type

            # Check for duplicate
            result = await db.execute(
                select(Asset).where(
                    Asset.project_id == project_id,
                    Asset.type == item_type,
                    Asset.value == item.value,
                )
            )
            if result.scalar_one_or_none():
                if data.skip_duplicates:
                    skipped += 1
                    continue
                else:
                    errors.append({"value": item.value, "error": "Duplicate asset"})
                    continue

            asset = Asset(
                project_id=project_id,
                type=item_type,
                value=item.value,
                metadata_=item.metadata_ if item.metadata_ else {},
                tags=item.tags if item.tags else [],
            )
            db.add(asset)
            imported += 1

        except Exception as e:
            errors.append({"value": item.value, "error": str(e)})

    await db.flush()

    return AssetImportResult(
        imported=imported,
        skipped=skipped,
        errors=errors,
    )


@router.post("/relations", response_model=AssetRelationResponse, status_code=status.HTTP_201_CREATED)
async def create_asset_relation(
    data: AssetRelationCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> AssetRelationResponse:
    """Create a relationship between two assets."""
    # Verify both assets exist and user has access
    parent_result = await db.execute(select(Asset).where(Asset.id == data.parent_id))
    parent = parent_result.scalar_one_or_none()
    if not parent:
        raise NotFoundError("Asset", str(data.parent_id))

    child_result = await db.execute(select(Asset).where(Asset.id == data.child_id))
    child = child_result.scalar_one_or_none()
    if not child:
        raise NotFoundError("Asset", str(data.child_id))

    # Check project access
    await check_project_access(db, parent.project_id, current_user.id, current_user.is_superuser)

    # Ensure both assets are in the same project
    if parent.project_id != child.project_id:
        raise ConflictError("Assets must be in the same project")

    # Check for existing relation
    existing = await db.execute(
        select(AssetRelation).where(
            AssetRelation.parent_id == data.parent_id,
            AssetRelation.child_id == data.child_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("Relationship already exists")

    # Handle both enum instances and string values (Pydantic v2 with use_enum_values)
    rel_type = data.relation_type.value if hasattr(data.relation_type, 'value') else data.relation_type

    relation = AssetRelation(
        parent_id=data.parent_id,
        child_id=data.child_id,
        relation_type=rel_type,
        metadata_=data.metadata_ if data.metadata_ else {},
    )
    db.add(relation)
    await db.flush()

    return AssetRelationResponse(
        parent_id=relation.parent_id,
        child_id=relation.child_id,
        relation_type=data.relation_type,
        parent_value=parent.value,
        child_value=child.value,
    )


@router.delete("/relations/{parent_id}/{child_id}", response_model=MessageResponse)
async def delete_asset_relation(
    parent_id: UUID,
    child_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Delete a relationship between two assets."""
    result = await db.execute(
        select(AssetRelation).where(
            AssetRelation.parent_id == parent_id,
            AssetRelation.child_id == child_id,
        )
    )
    relation = result.scalar_one_or_none()

    if not relation:
        raise NotFoundError("AssetRelation", f"{parent_id}-{child_id}")

    # Verify access through parent asset
    parent_result = await db.execute(select(Asset).where(Asset.id == parent_id))
    parent = parent_result.scalar_one_or_none()
    if parent:
        await check_project_access(db, parent.project_id, current_user.id, current_user.is_superuser)

    await db.delete(relation)
    return {"message": "Relationship deleted successfully", "success": True}


# =============================================================================
# PARAMETRIC ROUTES - Must come after specific routes
# =============================================================================

@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> AssetResponse:
    """Get an asset by ID."""
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise NotFoundError("Asset", str(asset_id))

    await check_project_access(db, asset.project_id, current_user.id, current_user.is_superuser)

    vuln_count = await db.scalar(
        select(func.count()).select_from(Vulnerability).where(Vulnerability.asset_id == asset.id)
    )
    cred_count = await db.scalar(
        select(func.count()).select_from(Credential).where(Credential.asset_id == asset.id)
    )

    return AssetResponse(
        id=asset.id,
        project_id=asset.project_id,
        type=AssetType(asset.type),
        value=asset.value,
        metadata=asset.metadata_,
        tags=asset.tags,
        status=AssetStatus(asset.status),
        risk_score=asset.risk_score,
        discovered_by=asset.discovered_by,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        vulnerability_count=vuln_count or 0,
        credential_count=cred_count or 0,
    )


@router.patch("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: UUID,
    data: AssetUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> AssetResponse:
    """Update an asset."""
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise NotFoundError("Asset", str(asset_id))

    await check_project_access(db, asset.project_id, current_user.id, current_user.is_superuser)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            # Handle both enum instances and string values
            status_value = value.value if hasattr(value, 'value') else value
            setattr(asset, field, status_value)
        elif field == "metadata_":
            asset.metadata_ = value
        elif hasattr(asset, field):
            setattr(asset, field, value)

    await db.flush()
    await db.refresh(asset)

    return AssetResponse(
        id=asset.id,
        project_id=asset.project_id,
        type=AssetType(asset.type),
        value=asset.value,
        metadata=asset.metadata_,
        tags=asset.tags,
        status=AssetStatus(asset.status),
        risk_score=asset.risk_score,
        discovered_by=asset.discovered_by,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


@router.delete("/{asset_id}", response_model=MessageResponse)
async def delete_asset(
    asset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Delete an asset."""
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise NotFoundError("Asset", str(asset_id))

    await check_project_access(db, asset.project_id, current_user.id, current_user.is_superuser)

    await db.delete(asset)

    return {"message": "Asset deleted successfully", "success": True}
