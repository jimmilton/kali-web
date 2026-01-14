"""Custom exceptions for the application."""

from typing import Any, Dict, Optional

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        code: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code


class AuthenticationError(AppException):
    """Authentication error exception."""

    def __init__(
        self,
        detail: str = "Could not validate credentials",
        code: str = "AUTHENTICATION_ERROR",
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            code=code,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(AppException):
    """Authorization error exception."""

    def __init__(
        self,
        detail: str = "Not enough permissions",
        code: str = "AUTHORIZATION_ERROR",
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            code=code,
        )


class NotFoundError(AppException):
    """Resource not found exception."""

    def __init__(
        self,
        resource: str = "Resource",
        resource_id: Optional[str] = None,
        code: str = "NOT_FOUND",
    ):
        detail = f"{resource} not found"
        if resource_id:
            detail = f"{resource} with id '{resource_id}' not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            code=code,
        )


class ValidationError(AppException):
    """Validation error exception."""

    def __init__(
        self,
        detail: str = "Validation error",
        code: str = "VALIDATION_ERROR",
        errors: Optional[list] = None,
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            code=code,
        )
        self.errors = errors or []


class ConflictError(AppException):
    """Conflict error exception (e.g., duplicate resource)."""

    def __init__(
        self,
        detail: str = "Resource already exists",
        code: str = "CONFLICT",
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            code=code,
        )


class RateLimitError(AppException):
    """Rate limit exceeded exception."""

    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        code: str = "RATE_LIMIT_EXCEEDED",
        retry_after: Optional[int] = None,
    ):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            code=code,
            headers=headers if headers else None,
        )


class ServiceUnavailableError(AppException):
    """Service unavailable exception."""

    def __init__(
        self,
        detail: str = "Service temporarily unavailable",
        code: str = "SERVICE_UNAVAILABLE",
    ):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            code=code,
        )


class BadRequestError(AppException):
    """Bad request exception."""

    def __init__(
        self,
        detail: str = "Bad request",
        code: str = "BAD_REQUEST",
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            code=code,
        )


class ToolExecutionError(AppException):
    """Tool execution error exception."""

    def __init__(
        self,
        detail: str = "Tool execution failed",
        code: str = "TOOL_EXECUTION_ERROR",
        tool_name: Optional[str] = None,
        exit_code: Optional[int] = None,
    ):
        if tool_name:
            detail = f"Tool '{tool_name}' execution failed: {detail}"
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            code=code,
        )
        self.tool_name = tool_name
        self.exit_code = exit_code


class WorkflowError(AppException):
    """Workflow execution error exception."""

    def __init__(
        self,
        detail: str = "Workflow execution failed",
        code: str = "WORKFLOW_ERROR",
        node_id: Optional[str] = None,
    ):
        if node_id:
            detail = f"Workflow failed at node '{node_id}': {detail}"
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            code=code,
        )
        self.node_id = node_id


class IntegrationError(AppException):
    """External integration error exception."""

    def __init__(
        self,
        detail: str = "Integration error",
        code: str = "INTEGRATION_ERROR",
        integration: Optional[str] = None,
    ):
        if integration:
            detail = f"Integration '{integration}' error: {detail}"
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
            code=code,
        )
        self.integration = integration
