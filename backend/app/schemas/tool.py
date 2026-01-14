"""Tool definition and configuration schemas."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.schemas.common import BaseSchema


class ParameterType(str, Enum):
    """Tool parameter type enumeration."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    FILE = "file"
    TARGET = "target"  # IP, domain, URL, etc.
    PORT = "port"
    PORT_RANGE = "port_range"
    WORDLIST = "wordlist"
    TEXTAREA = "textarea"
    SECRET = "secret"  # Sensitive data like passwords, API keys


class ToolCategory(str, Enum):
    """Tool category enumeration."""

    RECONNAISSANCE = "reconnaissance"
    VULNERABILITY_SCANNING = "vulnerability_scanning"
    WEB_APPLICATION = "web_application"
    PASSWORD_ATTACKS = "password_attacks"
    WIRELESS = "wireless"
    EXPLOITATION = "exploitation"
    POST_EXPLOITATION = "post_exploitation"
    FORENSICS = "forensics"
    REPORTING = "reporting"
    UTILITY = "utility"
    SOCIAL_ENGINEERING = "social_engineering"


class ToolParameter(BaseSchema):
    """Schema for tool parameter definition."""

    name: str
    label: str
    type: ParameterType
    description: Optional[str] = None
    required: bool = False
    default: Optional[Any] = None
    placeholder: Optional[str] = None

    # Validation
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # Regex pattern

    # Select options
    options: Optional[List[Dict[str, Any]]] = None
    # [{"value": "...", "label": "...", "description": "..."}]

    # Grouping
    group: Optional[str] = None
    advanced: bool = False

    # Conditional display
    depends_on: Optional[str] = None
    depends_value: Optional[Any] = None


class ToolOutput(BaseSchema):
    """Schema for tool output configuration."""

    format: str  # json, xml, text, csv
    parser: Optional[str] = None  # Parser class name
    creates_assets: bool = False
    creates_vulnerabilities: bool = False


class ToolDefinition(BaseSchema):
    """Schema for complete tool definition."""

    slug: str = Field(..., pattern=r"^[a-z0-9-]+$")
    name: str
    description: str
    category: ToolCategory
    version: Optional[str] = None

    # Docker configuration
    docker_image: str
    command_template: str
    # Template with placeholders: "nmap {target} -p {ports} {flags}"

    # Parameters
    parameters: List[ToolParameter] = []

    # Output configuration
    output: ToolOutput

    # Execution settings
    default_timeout: int = 3600
    max_timeout: int = 86400
    requires_root: bool = False
    network_mode: str = "bridge"  # bridge, host, none

    # Resource limits
    memory_limit: str = "2g"
    cpu_limit: float = 2.0

    # UI settings
    icon: Optional[str] = None
    color: Optional[str] = None
    documentation_url: Optional[str] = None

    # Tags for filtering
    tags: List[str] = []

    # Feature flags
    supports_streaming: bool = True
    supports_cancel: bool = True
    supports_interactive: bool = False


class ToolListResponse(BaseSchema):
    """Schema for tool list response."""

    tools: List[ToolDefinition]
    categories: List[Dict[str, Any]]


class ToolExecutionPreview(BaseSchema):
    """Schema for tool execution preview."""

    command: str
    parameters: Dict[str, Any]
    estimated_duration: Optional[str] = None
    warnings: List[str] = []


class WordlistInfo(BaseSchema):
    """Schema for wordlist information."""

    name: str
    path: str
    size: int
    line_count: int
    description: Optional[str] = None
    category: str  # passwords, directories, subdomains, etc.
