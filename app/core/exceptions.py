"""
Custom exception classes for the Amazon Product Intelligence Platform.
"""
from typing import Any, Dict, Optional


class BaseAPIException(Exception):
    """Base exception class for all API-related errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BaseAPIException):
    """Exception for input validation errors."""
    
    def __init__(
        self,
        message: str = "Validation error",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details or {}
        )
        if field:
            self.details["field"] = field


class AuthenticationError(BaseAPIException):
    """Exception for authentication failures."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details or {}
        )


class AuthorizationError(BaseAPIException):
    """Exception for authorization failures."""
    
    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            details=details or {}
        )
        if required_permission:
            self.details["required_permission"] = required_permission


class ResourceNotFoundError(BaseAPIException):
    """Exception for resource not found errors."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details=details or {}
        )
        if resource_type:
            self.details["resource_type"] = resource_type
        if resource_id:
            self.details["resource_id"] = resource_id


class ConflictError(BaseAPIException):
    """Exception for resource conflict errors."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        conflicting_field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT_ERROR",
            details=details or {}
        )
        if conflicting_field:
            self.details["conflicting_field"] = conflicting_field


class RateLimitError(BaseAPIException):
    """Exception for rate limit exceeded errors."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details or {}
        )
        if retry_after:
            self.details["retry_after"] = retry_after
        if limit_type:
            self.details["limit_type"] = limit_type


class InsufficientCreditsError(BaseAPIException):
    """Exception for insufficient credits errors."""
    
    def __init__(
        self,
        message: str = "Insufficient credits",
        required_credits: Optional[int] = None,
        available_credits: Optional[int] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=402,
            error_code="INSUFFICIENT_CREDITS",
            details=details or {}
        )
        if required_credits is not None:
            self.details["required_credits"] = required_credits
        if available_credits is not None:
            self.details["available_credits"] = available_credits
        if operation:
            self.details["operation"] = operation


class ExternalServiceError(BaseAPIException):
    """Exception for external service errors."""
    
    def __init__(
        self,
        message: str = "External service error",
        service_name: Optional[str] = None,
        service_error_code: Optional[str] = None,
        is_temporary: bool = True,
        details: Optional[Dict[str, Any]] = None
    ):
        status_code = 503 if is_temporary else 502
        super().__init__(
            message=message,
            status_code=status_code,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details or {}
        )
        if service_name:
            self.details["service_name"] = service_name
        if service_error_code:
            self.details["service_error_code"] = service_error_code
        self.details["is_temporary"] = is_temporary


class PaymentError(BaseAPIException):
    """Exception for payment processing errors."""
    
    def __init__(
        self,
        message: str = "Payment processing error",
        payment_intent_id: Optional[str] = None,
        stripe_error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=402,
            error_code="PAYMENT_ERROR",
            details=details or {}
        )
        if payment_intent_id:
            self.details["payment_intent_id"] = payment_intent_id
        if stripe_error_code:
            self.details["stripe_error_code"] = stripe_error_code


class DataIntegrityError(BaseAPIException):
    """Exception for data integrity errors."""
    
    def __init__(
        self,
        message: str = "Data integrity error",
        constraint_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=422,
            error_code="DATA_INTEGRITY_ERROR",
            details=details or {}
        )
        if constraint_name:
            self.details["constraint_name"] = constraint_name


class ConfigurationError(BaseAPIException):
    """Exception for configuration errors."""
    
    def __init__(
        self,
        message: str = "Configuration error",
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=500,
            error_code="CONFIGURATION_ERROR",
            details=details or {}
        )
        if config_key:
            self.details["config_key"] = config_key


class MaintenanceModeError(BaseAPIException):
    """Exception for maintenance mode errors."""
    
    def __init__(
        self,
        message: str = "Service temporarily unavailable for maintenance",
        estimated_duration: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=503,
            error_code="MAINTENANCE_MODE",
            details=details or {}
        )
        if estimated_duration:
            self.details["estimated_duration_seconds"] = estimated_duration


# Amazon-specific exceptions
class ProductNotFoundError(ResourceNotFoundError):
    """Exception for Amazon product not found errors."""
    
    def __init__(
        self,
        asin: str,
        marketplace: str = "US",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Product not found: {asin}",
            resource_type="product",
            resource_id=asin,
            details=details or {}
        )
        self.details["marketplace"] = marketplace
        self.error_code = "PRODUCT_NOT_FOUND"


class InvalidASINError(ValidationError):
    """Exception for invalid ASIN format errors."""
    
    def __init__(
        self,
        asin: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Invalid ASIN format: {asin}",
            field="asin",
            details=details or {}
        )
        self.error_code = "INVALID_ASIN"


class InvalidFNSKUError(ValidationError):
    """Exception for invalid FNSKU format errors."""
    
    def __init__(
        self,
        fnsku: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Invalid FNSKU format: {fnsku}",
            field="fnsku",
            details=details or {}
        )
        self.error_code = "INVALID_FNSKU"


class ConversionFailedError(ExternalServiceError):
    """Exception for FNSKU to ASIN conversion failures."""
    
    def __init__(
        self,
        fnsku: str,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"Conversion failed for FNSKU: {fnsku}"
        if reason:
            message += f" - {reason}"
        
        super().__init__(
            message=message,
            service_name="fnsku_conversion",
            is_temporary=False,
            details=details or {}
        )
        self.details["fnsku"] = fnsku
        self.error_code = "CONVERSION_FAILED"


# Database-specific exceptions
class DatabaseConnectionError(BaseAPIException):
    """Exception for database connection errors."""
    
    def __init__(
        self,
        message: str = "Database connection error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=503,
            error_code="DATABASE_CONNECTION_ERROR",
            details=details or {}
        )


class DatabaseTimeoutError(BaseAPIException):
    """Exception for database timeout errors."""
    
    def __init__(
        self,
        message: str = "Database operation timeout",
        operation: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=504,
            error_code="DATABASE_TIMEOUT",
            details=details or {}
        )
        if operation:
            self.details["operation"] = operation
        if timeout_seconds:
            self.details["timeout_seconds"] = timeout_seconds


# Cache-specific exceptions
class CacheError(BaseAPIException):
    """Exception for cache-related errors."""
    
    def __init__(
        self,
        message: str = "Cache operation error",
        cache_key: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=500,
            error_code="CACHE_ERROR",
            details=details or {}
        )
        if cache_key:
            self.details["cache_key"] = cache_key
        if operation:
            self.details["operation"] = operation


# Business logic exceptions
class BusinessRuleViolationError(BaseAPIException):
    """Exception for business rule violations."""
    
    def __init__(
        self,
        message: str = "Business rule violation",
        rule_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=422,
            error_code="BUSINESS_RULE_VIOLATION",
            details=details or {}
        )
        if rule_name:
            self.details["rule_name"] = rule_name


class QuotaExceededError(BaseAPIException):
    """Exception for quota exceeded errors."""
    
    def __init__(
        self,
        message: str = "Quota exceeded",
        quota_type: Optional[str] = None,
        current_usage: Optional[int] = None,
        quota_limit: Optional[int] = None,
        reset_time: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=429,
            error_code="QUOTA_EXCEEDED",
            details=details or {}
        )
        if quota_type:
            self.details["quota_type"] = quota_type
        if current_usage is not None:
            self.details["current_usage"] = current_usage
        if quota_limit is not None:
            self.details["quota_limit"] = quota_limit
        if reset_time:
            self.details["reset_time"] = reset_time