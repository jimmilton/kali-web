"""Tools API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.schemas.tool import ToolCategory, ToolDefinition, ToolExecutionPreview, ToolListResponse
from app.tools.registry import get_tool, get_tools_by_category, list_all_tools

router = APIRouter()


@router.get("", response_model=ToolListResponse)
async def list_tools(
    current_user: CurrentUser,
    category: Optional[ToolCategory] = None,
    search: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
) -> ToolListResponse:
    """List available tools."""
    if category:
        tools = get_tools_by_category(category)
    else:
        tools = list_all_tools()

    # Filter by search
    if search:
        search_lower = search.lower()
        tools = [
            t for t in tools
            if search_lower in t.name.lower()
            or search_lower in t.description.lower()
            or search_lower in t.slug.lower()
        ]

    # Filter by tags
    if tags:
        tools = [t for t in tools if any(tag in t.tags for tag in tags)]

    # Get categories with counts
    all_tools = list_all_tools()
    categories = []
    for cat in ToolCategory:
        count = len([t for t in all_tools if t.category == cat])
        if count > 0:
            categories.append({
                "id": cat.value,
                "name": cat.value.replace("_", " ").title(),
                "count": count,
            })

    return ToolListResponse(tools=tools, categories=categories)


@router.get("/{slug}", response_model=ToolDefinition)
async def get_tool_definition(
    slug: str,
    current_user: CurrentUser,
) -> ToolDefinition:
    """Get tool definition by slug."""
    tool = get_tool(slug)
    if not tool:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Tool", slug)
    return tool


@router.post("/{slug}/preview", response_model=ToolExecutionPreview)
async def preview_tool_execution(
    slug: str,
    parameters: dict,
    current_user: CurrentUser,
) -> ToolExecutionPreview:
    """Preview the command that would be executed."""
    tool = get_tool(slug)
    if not tool:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Tool", slug)

    # Build command from template
    command = tool.command_template
    warnings = []

    for param in tool.parameters:
        param_value = parameters.get(param.name)
        placeholder = "{" + param.name + "}"

        if param_value is not None:
            # Handle both enum instances and string values (Pydantic v2 with use_enum_values)
            param_type = param.type.value if hasattr(param.type, 'value') else param.type

            # Handle different parameter types
            if param_type == "boolean":
                if param_value:
                    command = command.replace(placeholder, param.name)
                else:
                    command = command.replace(placeholder, "")
            elif param_type == "select":
                command = command.replace(placeholder, str(param_value))
            else:
                command = command.replace(placeholder, str(param_value))
        elif param.required:
            warnings.append(f"Required parameter '{param.name}' is missing")
            command = command.replace(placeholder, "")
        else:
            command = command.replace(placeholder, param.default or "")

    # Clean up extra spaces
    command = " ".join(command.split())

    return ToolExecutionPreview(
        command=command,
        parameters=parameters,
        warnings=warnings,
    )
