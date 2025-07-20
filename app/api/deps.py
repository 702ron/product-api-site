"""
API dependencies and utilities for request validation, rate limiting, and common operations.
"""
import time
import hashlib
import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.models import User, AdminUser
from app.middleware.admin_auth import get_admin_user_from_token, require_admin_permission, require_admin_role

logger = logging.getLogger(__name__)
security = HTTPBearer()


class RateLimiter:
    """In-memory rate limiter for API endpoints."""
    
    def __init__(self):
        self.requests: Dict[str, Dict[str, Any]] = {}
        
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier for rate limiting."""
        # Try to get user ID from request state if authenticated
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    def _clean_old_requests(self, client_id: str, window_seconds: int):
        """Clean up old requests outside the time window."""
        current_time = time.time()
        if client_id in self.requests:
            self.requests[client_id]["timestamps"] = [
                timestamp for timestamp in self.requests[client_id]["timestamps"]
                if current_time - timestamp < window_seconds
            ]
    
    async def check_rate_limit(
        self,
        request: Request,
        calls_per_minute: int = 60,
        calls_per_second: int = 10
    ) -> bool:
        """
        Check if request is within rate limits.
        
        Args:
            request: FastAPI request object
            calls_per_minute: Maximum calls per minute
            calls_per_second: Maximum calls per second
            
        Returns:
            True if within limits
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        # Initialize client data
        if client_id not in self.requests:
            self.requests[client_id] = {
                "timestamps": [],
                "last_request": 0
            }
        
        client_data = self.requests[client_id]
        
        # Check per-second limit
        if current_time - client_data["last_request"] < (1.0 / calls_per_second):
            logger.warning(f"Rate limit exceeded (per-second) for {client_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down your requests.",
                headers={"Retry-After": "1"}
            )
        
        # Check per-minute limit
        self._clean_old_requests(client_id, 60)  # Clean requests older than 1 minute
        
        if len(client_data["timestamps"]) >= calls_per_minute:
            oldest_request = min(client_data["timestamps"])
            retry_after = int(60 - (current_time - oldest_request)) + 1
            
            logger.warning(f"Rate limit exceeded (per-minute) for {client_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(retry_after)}
            )
        
        # Record this request
        client_data["timestamps"].append(current_time)
        client_data["last_request"] = current_time
        
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


async def apply_rate_limit(request: Request):
    """Dependency to apply rate limiting to endpoints."""
    await rate_limiter.check_rate_limit(request)
    return True


async def apply_strict_rate_limit(request: Request):
    """Dependency for stricter rate limiting on expensive endpoints."""
    await rate_limiter.check_rate_limit(
        request,
        calls_per_minute=30,  # Reduced limit
        calls_per_second=2    # Reduced limit
    )
    return True


async def get_request_id(request: Request) -> str:
    """Generate or extract request ID for tracing."""
    # Check if request ID already exists in headers
    request_id = request.headers.get("X-Request-ID")
    
    if not request_id:
        # Generate new request ID
        timestamp = str(int(time.time() * 1000))
        client_ip = request.client.host if request.client else "unknown"
        unique_string = f"{timestamp}:{client_ip}:{request.url.path}"
        request_id = hashlib.md5(unique_string.encode()).hexdigest()[:12]
    
    return request_id


async def get_client_info(request: Request) -> Dict[str, Any]:
    """Extract client information from request."""
    return {
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("User-Agent", "unknown"),
        "forwarded_for": request.headers.get("X-Forwarded-For"),
        "referer": request.headers.get("Referer"),
        "origin": request.headers.get("Origin"),
        "request_id": await get_request_id(request)
    }


async def validate_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Validate API key from Authorization header.
    
    This is an alternative authentication method for machine-to-machine access.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    api_key = credentials.credentials
    
    # TODO: Implement actual API key validation against database
    # For now, this is a placeholder
    if not api_key or len(api_key) < 32:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # In a real implementation, validate against API keys table
    # and return associated user or organization ID
    return api_key


async def require_admin_user(
    admin_user: AdminUser = Depends(get_admin_user_from_token)
) -> AdminUser:
    """Dependency that requires admin privileges."""
    if not admin_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return admin_user


async def require_super_admin(
    admin_user: AdminUser = Depends(require_admin_role("super_admin"))
) -> AdminUser:
    """Dependency that requires super admin privileges."""
    return admin_user


async def apply_admin_rate_limit(request: Request):
    """Dependency for admin endpoints with higher rate limits."""
    await rate_limiter.check_rate_limit(
        request,
        calls_per_minute=500,  # Higher limit for admin users
        calls_per_second=20    # Higher limit for admin users
    )
    return True


async def validate_content_type(request: Request):
    """Validate request content type for POST/PUT endpoints."""
    if request.method in ["POST", "PUT", "PATCH"]:
        content_type = request.headers.get("Content-Type", "")
        
        if not content_type.startswith("application/json"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Content-Type must be application/json"
            )
    
    return True


async def validate_request_size(request: Request, max_size_mb: int = 10):
    """Validate request body size."""
    content_length = request.headers.get("Content-Length")
    
    if content_length:
        content_length = int(content_length)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if content_length > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Request body too large. Maximum size: {max_size_mb}MB"
            )
    
    return True


class PaginationParams:
    """Pagination parameters for list endpoints."""
    
    def __init__(
        self,
        skip: int = 0,
        limit: int = 50,
        max_limit: int = 1000
    ):
        if skip < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Skip parameter must be non-negative"
            )
        
        if limit <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit parameter must be positive"
            )
        
        if limit > max_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Limit parameter cannot exceed {max_limit}"
            )
        
        self.skip = skip
        self.limit = limit


async def get_pagination_params(
    skip: int = 0,
    limit: int = 50
) -> PaginationParams:
    """Dependency for pagination parameters."""
    return PaginationParams(skip=skip, limit=limit)


async def log_api_usage(
    request: Request,
    response_time_ms: Optional[int] = None,
    credits_used: Optional[int] = None,
    user: Optional[User] = None
):
    """Log API usage for monitoring and analytics."""
    try:
        client_info = await get_client_info(request)
        
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": client_info["ip_address"],
            "user_agent": client_info["user_agent"],
            "request_id": client_info["request_id"],
            "user_id": str(user.id) if user else None,
            "response_time_ms": response_time_ms,
            "credits_used": credits_used,
            "timestamp": time.time()
        }
        
        logger.info(f"API Usage: {log_data}")
        
    except Exception as e:
        logger.error(f"Error logging API usage: {str(e)}")


async def check_maintenance_mode():
    """Check if API is in maintenance mode."""
    # TODO: Implement maintenance mode check
    # This could check a database flag, environment variable, or config file
    maintenance_mode = False  # Placeholder
    
    if maintenance_mode:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API is currently in maintenance mode. Please try again later.",
            headers={"Retry-After": "3600"}  # 1 hour
        )
    
    return True


async def validate_marketplace(marketplace: str = "US") -> str:
    """Validate Amazon marketplace parameter."""
    valid_marketplaces = {
        "US", "CA", "MX", "BR",  # Americas
        "GB", "DE", "FR", "IT", "ES", "NL", "SE", "PL", "TR",  # Europe
        "JP", "AU", "SG", "IN", "AE", "SA", "EG"  # Asia-Pacific & Middle East
    }
    
    marketplace = marketplace.upper()
    
    if marketplace not in valid_marketplaces:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid marketplace. Supported: {', '.join(sorted(valid_marketplaces))}"
        )
    
    return marketplace


async def enhanced_error_context(request: Request) -> Dict[str, Any]:
    """Provide enhanced error context for debugging."""
    client_info = await get_client_info(request)
    
    return {
        "request_id": client_info["request_id"],
        "timestamp": time.time(),
        "method": request.method,
        "url": str(request.url),
        "client_ip": client_info["ip_address"],
        "user_agent": client_info["user_agent"],
        "headers": dict(request.headers)
    }