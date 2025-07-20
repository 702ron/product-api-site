"""
Pydantic schemas for admin API endpoints.
"""
from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


# Base schemas
class AdminUserBase(BaseModel):
    """Base admin user schema."""
    admin_role: str
    permissions: Optional[dict[str, Any]] = None
    is_active: bool = True


class UserBase(BaseModel):
    """Base user schema."""
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    credit_balance: int = 0


# Request schemas
class AdminUserCreateRequest(BaseModel):
    """Schema for creating admin users."""
    user_id: str
    admin_role: str = Field(..., pattern="^(super_admin|admin|moderator|viewer)$")
    permissions: Optional[dict[str, Any]] = None


class AdminUserUpdateRequest(BaseModel):
    """Schema for updating admin users."""
    admin_role: Optional[str] = Field(None, pattern="^(super_admin|admin|moderator|viewer)$")
    permissions: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class UserCreateRequest(BaseModel):
    """Schema for creating regular users."""
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    full_name: Optional[str] = None
    credit_balance: int = Field(default=10, ge=0)
    password: Optional[str] = Field(None, min_length=8)


class UserUpdateRequest(BaseModel):
    """Schema for updating users."""
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class CreditAdjustmentRequest(BaseModel):
    """Schema for credit adjustments."""
    amount: int = Field(..., description="Amount to adjust (positive to add, negative to subtract)")
    reason: str = Field(..., min_length=3, max_length=500)


# Response schemas
class UserResponse(BaseModel):
    """Basic user response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    credit_balance: int
    created_at: datetime
    updated_at: datetime


class AdminUserResponse(BaseModel):
    """Admin user response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    admin_role: str
    permissions: Optional[dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Nested user data
    user: UserResponse


class AdminUserListResponse(BaseModel):
    """Schema for admin user list items."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    credit_balance: int
    created_at: datetime

    # Admin info if user is admin
    admin_role: Optional[str] = None
    admin_permissions: Optional[dict[str, Any]] = None


class AdminUserDetailResponse(BaseModel):
    """Detailed user response with activity stats."""
    model_config = ConfigDict(from_attributes=True)

    # Basic user info
    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    credit_balance: int
    created_at: datetime
    updated_at: datetime

    # Admin info if applicable
    admin_role: Optional[str] = None
    admin_permissions: Optional[dict[str, Any]] = None

    # Activity stats
    total_queries: int = 0
    total_credits_spent: int = 0
    total_credits_purchased: int = 0
    last_login: Optional[datetime] = None
    last_activity: Optional[datetime] = None

    # Recent activity counts
    queries_last_30_days: int = 0
    credits_spent_last_30_days: int = 0


class PaginatedUsersResponse(BaseModel):
    """Paginated users response."""
    users: list[AdminUserListResponse]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_previous: bool


class UserStatsResponse(BaseModel):
    """Comprehensive user statistics."""
    user_id: str
    email: str

    # Usage statistics
    total_queries: int
    successful_queries: int
    failed_queries: int

    # Credit statistics
    total_credits_purchased: int
    total_credits_spent: int
    current_credit_balance: int

    # Time-based statistics
    queries_by_month: dict[str, int]
    credits_spent_by_month: dict[str, int]

    # Query type breakdown
    query_types: dict[str, int]

    # Performance metrics
    average_response_time_ms: Optional[float]

    # Account metrics
    account_age_days: int
    last_login: Optional[datetime]
    last_query: Optional[datetime]


# System monitoring schemas
class SystemHealthResponse(BaseModel):
    """System health status."""
    status: str = Field(..., description="Overall system status")
    timestamp: datetime
    components: dict[str, dict[str, Any]]
    uptime_seconds: int
    version: str


class SystemMetricsResponse(BaseModel):
    """System performance metrics."""
    timestamp: datetime

    # API metrics
    requests_per_minute: float
    average_response_time_ms: float
    error_rate_percent: float

    # Database metrics
    database_connections: int
    database_query_time_ms: float

    # Cache metrics
    cache_hit_rate_percent: float
    cache_memory_usage_mb: float

    # System resources
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float


class ApiAnalyticsResponse(BaseModel):
    """API usage analytics."""
    time_period: str
    total_requests: int
    unique_users: int

    # Endpoint popularity
    popular_endpoints: list[dict[str, Union[str, int]]]

    # Response time distribution
    response_time_percentiles: dict[str, float]

    # Error analysis
    error_breakdown: dict[str, int]

    # User activity
    active_users_by_day: dict[str, int]

    # Credit usage
    credits_consumed: int
    revenue_generated: float


# Billing schemas
class BillingOverviewResponse(BaseModel):
    """Billing system overview."""
    total_revenue: float
    monthly_recurring_revenue: float
    active_subscriptions: int

    # Revenue breakdown
    revenue_by_plan: dict[str, float]
    revenue_by_month: dict[str, float]

    # Credit sales
    total_credits_sold: int
    credits_revenue: float

    # Churn metrics
    churn_rate_percent: float
    new_customers_this_month: int


class SubscriptionResponse(BaseModel):
    """Subscription details."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    stripe_subscription_id: str
    status: str
    plan_name: str
    amount: float
    currency: str
    created_at: datetime
    current_period_start: datetime
    current_period_end: datetime

    user: UserResponse


# Content moderation schemas
class ContentModerationResponse(BaseModel):
    """Content moderation queue item."""
    id: str
    content_type: str
    content_id: str
    status: str
    reported_reason: str
    reported_by: Optional[str]
    created_at: datetime

    # Content preview
    content_preview: dict[str, Any]


# Configuration schemas
class SystemConfigResponse(BaseModel):
    """System configuration item."""
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: Any
    description: Optional[str]
    config_type: str
    is_sensitive: bool
    requires_restart: bool
    updated_at: datetime


class SystemConfigUpdateRequest(BaseModel):
    """Update system configuration."""
    value: Any
    description: Optional[str] = None


# Audit logging schemas
class AuditLogResponse(BaseModel):
    """Audit log entry."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    admin_user_id: str
    action_type: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    success: bool
    error_message: Optional[str]
    duration_ms: Optional[int]

    # Nested admin user info
    admin_user: AdminUserResponse


class PaginatedAuditLogsResponse(BaseModel):
    """Paginated audit logs response."""
    logs: list[AuditLogResponse]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_previous: bool


# Security monitoring schemas
class SecurityEventResponse(BaseModel):
    """Security event details."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    severity: str
    user_id: Optional[str]
    admin_user_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Optional[dict[str, Any]]
    resolved: bool
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime
    source: Optional[str]
    risk_score: Optional[int]
    false_positive: bool


class SecurityEventUpdateRequest(BaseModel):
    """Update security event."""
    resolved: bool
    false_positive: Optional[bool] = None
    resolution_notes: Optional[str] = None


class SecurityDashboardResponse(BaseModel):
    """Security monitoring dashboard."""
    timestamp: datetime

    # Alert counts
    open_alerts: int
    high_severity_alerts: int
    critical_alerts: int

    # Recent activity
    failed_logins_24h: int
    suspicious_activity_24h: int
    blocked_ips: list[str]

    # Risk assessment
    overall_risk_score: int
    top_risks: list[dict[str, Any]]


# Export schemas
class ExportJobResponse(BaseModel):
    """Data export job details."""
    id: str
    export_type: str
    status: str
    format: str
    parameters: dict[str, Any]
    file_url: Optional[str]
    file_size_bytes: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
    expires_at: Optional[datetime]
    error_message: Optional[str]


class ExportJobCreateRequest(BaseModel):
    """Create data export job."""
    export_type: str = Field(..., pattern="^(users|transactions|queries|audit_logs|security_events)$")
    format: str = Field(default="csv", pattern="^(csv|json|xlsx)$")
    parameters: Optional[dict[str, Any]] = Field(default_factory=dict)

    # Date range
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Filters
    filters: Optional[dict[str, Any]] = Field(default_factory=dict)


# Notification schemas
class NotificationResponse(BaseModel):
    """Admin notification."""
    id: str
    type: str
    title: str
    message: str
    severity: str
    read: bool
    created_at: datetime

    # Contextual data
    data: Optional[dict[str, Any]] = None


class NotificationCreateRequest(BaseModel):
    """Create admin notification."""
    type: str
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=1000)
    severity: str = Field(default="info", pattern="^(info|warning|error|critical)$")
    recipients: Optional[list[str]] = None  # Admin user IDs, None for all admins
    data: Optional[dict[str, Any]] = None
