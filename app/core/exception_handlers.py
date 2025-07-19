"""
Global exception handlers for structured error responses.
"""
import logging
import traceback
from datetime import datetime
from typing import Any, Dict
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import BaseAPIException
from app.api.deps import get_request_id, enhanced_error_context

logger = logging.getLogger(__name__)


async def create_error_response(
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
    details: Dict[str, Any] = None,
    include_trace: bool = False
) -> JSONResponse:
    """
    Create standardized error response.
    
    Args:
        request: FastAPI request object
        status_code: HTTP status code
        error_code: Application-specific error code
        message: Human-readable error message
        details: Additional error details
        include_trace: Whether to include stack trace (debug mode only)
        
    Returns:
        JSONResponse with structured error format
    """
    request_id = await get_request_id(request)
    
    error_response = {
        "error": {
            "code": error_code,
            "message": message,
            "status_code": status_code,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "path": request.url.path
        }
    }
    
    if details:
        error_response["error"]["details"] = details
    
    # Include stack trace in debug mode
    if include_trace:
        error_response["error"]["trace"] = traceback.format_exc()
    
    # Add helpful links for common errors
    if status_code == 400:
        error_response["error"]["help"] = "Check your request format and parameters"
    elif status_code == 401:
        error_response["error"]["help"] = "Please check your authentication credentials"
    elif status_code == 402:
        error_response["error"]["help"] = "Please add credits to your account to continue"
    elif status_code == 403:
        error_response["error"]["help"] = "You don't have permission to access this resource"
    elif status_code == 404:
        error_response["error"]["help"] = "The requested resource was not found"
    elif status_code == 429:
        error_response["error"]["help"] = "Please slow down your requests or try again later"
    elif status_code >= 500:
        error_response["error"]["help"] = "Please try again later or contact support if the issue persists"
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


async def base_api_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """Handle custom BaseAPIException errors."""
    logger.error(
        f"API Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return await create_error_response(
        request=request,
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException errors."""
    error_code = "HTTP_ERROR"
    
    # Map common HTTP status codes to error codes
    status_code_mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT"
    }
    
    error_code = status_code_mapping.get(exc.status_code, "HTTP_ERROR")
    
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return await create_error_response(
        request=request,
        status_code=exc.status_code,
        error_code=error_code,
        message=str(exc.detail) if exc.detail else "HTTP error occurred"
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    logger.warning(
        f"Validation Error: {exc.errors()}",
        extra={
            "errors": exc.errors(),
            "path": request.url.path,
            "method": request.method
        }
    )
    
    # Format validation errors
    formatted_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        formatted_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    return await create_error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        details={
            "validation_errors": formatted_errors,
            "error_count": len(formatted_errors)
        }
    )


async def pydantic_validation_exception_handler(request: Request, exc: PydanticValidationError) -> JSONResponse:
    """Handle Pydantic ValidationError from models."""
    logger.warning(
        f"Pydantic Validation Error: {exc.errors()}",
        extra={
            "errors": exc.errors(),
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return await create_error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="MODEL_VALIDATION_ERROR",
        message="Data model validation failed",
        details={"validation_errors": exc.errors()}
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors."""
    error_context = await enhanced_error_context(request)
    
    # Log detailed error for debugging
    logger.error(
        f"Database Error: {type(exc).__name__} - {str(exc)}",
        extra={
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "request_context": error_context
        }
    )
    
    # Handle specific database errors
    if isinstance(exc, IntegrityError):
        # Extract constraint information if available
        constraint_detail = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
        
        return await create_error_response(
            request=request,
            status_code=status.HTTP_409_CONFLICT,
            error_code="DATA_INTEGRITY_ERROR",
            message="Data integrity constraint violation",
            details={
                "constraint_detail": constraint_detail,
                "hint": "Check for duplicate values or missing references"
            }
        )
    
    # Generic database error
    return await create_error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="DATABASE_ERROR",
        message="Database operation failed",
        details={
            "error_type": type(exc).__name__,
            "hint": "Please try again later or contact support"
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    error_context = await enhanced_error_context(request)
    
    # Log detailed error for debugging
    logger.error(
        f"Unexpected Error: {type(exc).__name__} - {str(exc)}",
        extra={
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": traceback.format_exc(),
            "request_context": error_context
        }
    )
    
    # Don't expose internal error details to users in production
    from app.core.config import settings
    include_trace = settings.debug
    
    return await create_error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
        details={
            "error_type": type(exc).__name__,
            "support_message": "Please contact support with the request ID if this issue persists"
        },
        include_trace=include_trace
    )


# Error monitoring and alerting
async def log_critical_error(
    request: Request,
    exc: Exception,
    context: Dict[str, Any] = None
):
    """Log critical errors for monitoring and alerting."""
    error_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "traceback": traceback.format_exc(),
        "request_method": request.method,
        "request_path": request.url.path,
        "request_id": await get_request_id(request),
        "user_agent": request.headers.get("User-Agent"),
        "client_ip": request.client.host if request.client else "unknown"
    }
    
    if context:
        error_data.update(context)
    
    # In a production environment, this would also send alerts to
    # monitoring systems like Sentry, DataDog, or CloudWatch
    logger.critical(f"Critical Error: {error_data}")


def add_exception_handlers(app):
    """Add all exception handlers to the FastAPI app."""
    
    # Custom exception handlers
    app.add_exception_handler(BaseAPIException, base_api_exception_handler)
    
    # FastAPI built-in exception handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, pydantic_validation_exception_handler)
    
    # Database exception handlers
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    
    # Catch-all exception handler
    app.add_exception_handler(Exception, generic_exception_handler)