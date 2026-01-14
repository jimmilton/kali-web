"""Import API endpoints for external scan results."""

from __future__ import annotations

import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.job import Job, JobStatus
from app.models.project import Project
from app.tools.parsers import get_parser

logger = logging.getLogger(__name__)

router = APIRouter()


class ImportResult(BaseModel):
    """Result of an import operation."""

    success: bool
    format: str
    assets_created: int
    assets_updated: int
    vulnerabilities_created: int
    vulnerabilities_updated: int
    credentials_created: int
    credentials_updated: int
    errors: list[str]


class ImportFormats(BaseModel):
    """Available import formats."""

    formats: list[dict]


SUPPORTED_FORMATS = {
    "nessus": {
        "name": "Nessus",
        "extensions": [".nessus", ".xml"],
        "parser": "nessus_parser",
        "description": "Nessus scan results (.nessus or .xml)",
    },
    "burp": {
        "name": "Burp Suite",
        "extensions": [".xml"],
        "parser": "burp_parser",
        "description": "Burp Suite XML export",
    },
    "nuclei": {
        "name": "Nuclei",
        "extensions": [".json", ".jsonl"],
        "parser": "nuclei_parser",
        "description": "Nuclei JSON/JSONL output",
    },
    "nmap": {
        "name": "Nmap",
        "extensions": [".xml"],
        "parser": "nmap_parser",
        "description": "Nmap XML output (-oX)",
    },
}


@router.get("/formats", response_model=ImportFormats)
async def list_import_formats() -> ImportFormats:
    """List available import formats."""
    formats = [
        {
            "id": format_id,
            "name": info["name"],
            "extensions": info["extensions"],
            "description": info["description"],
        }
        for format_id, info in SUPPORTED_FORMATS.items()
    ]
    return ImportFormats(formats=formats)


@router.post("/{format_type}", response_model=ImportResult)
async def import_scan_results(
    format_type: Literal["nessus", "burp", "nuclei", "nmap"],
    current_user: CurrentUser,
    db: DbSession,
    project_id: UUID = Query(..., description="Target project ID"),
    file: UploadFile = File(...),
) -> ImportResult:
    """
    Import scan results from external tools.

    Supported formats:
    - **nessus**: Nessus .nessus or XML files
    - **burp**: Burp Suite XML export
    - **nuclei**: Nuclei JSON/JSONL output
    - **nmap**: Nmap XML output (-oX)

    The imported results will be parsed and added to the specified project,
    creating new assets and vulnerabilities as appropriate.
    """
    # Validate format
    if format_type not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {format_type}. Supported formats: {list(SUPPORTED_FORMATS.keys())}",
        )

    format_info = SUPPORTED_FORMATS[format_type]

    # Validate file extension
    if file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext and ext not in format_info["extensions"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension for {format_type}. Expected: {format_info['extensions']}",
            )

    # Verify project exists and user has access
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check user has access to project
    if project.owner_id != current_user.id:
        # Check if user is a member
        from app.models.project import ProjectMember
        member_result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user.id,
            )
        )
        if not member_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project",
            )

    # Read file content
    try:
        content = await file.read()
        # Decode content, handling different encodings
        try:
            file_content = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                file_content = content.decode("latin-1")
            except UnicodeDecodeError:
                file_content = content.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {e}",
        )

    # Get parser
    parser = get_parser(format_info["parser"])
    if not parser:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Parser not available for format: {format_type}",
        )

    # Create a synthetic job for tracking
    job = Job(
        project_id=project_id,
        tool_name=f"import_{format_type}",
        parameters={"source_file": file.filename, "format": format_type},
        status=JobStatus.COMPLETED.value,
        created_by=current_user.id,
    )
    db.add(job)
    await db.flush()

    # Parse the content
    try:
        parse_output = parser.parse(file_content, job)
    except Exception as e:
        logger.exception(f"Failed to parse {format_type} file: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse file: {e}",
        )

    # Save results to database
    try:
        stats = await parser.save_results(db, job, parse_output)
    except Exception as e:
        logger.exception(f"Failed to save import results: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save import results: {e}",
        )

    logger.info(
        f"Import complete for project {project_id}: "
        f"{stats['assets_created']} assets created, "
        f"{stats['vulnerabilities_created']} vulnerabilities created"
    )

    return ImportResult(
        success=True,
        format=format_type,
        assets_created=stats.get("assets_created", 0),
        assets_updated=stats.get("assets_updated", 0),
        vulnerabilities_created=stats.get("vulnerabilities_created", 0),
        vulnerabilities_updated=stats.get("vulnerabilities_updated", 0),
        credentials_created=stats.get("credentials_created", 0),
        credentials_updated=stats.get("credentials_updated", 0),
        errors=parse_output.errors,
    )
