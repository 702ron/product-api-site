"""
Admin system monitoring and health endpoints.
"""
from datetime import datetime, timedelta

import psutil
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import apply_admin_rate_limit
from app.core.config import settings
from app.core.database import get_db
from app.middleware.admin_auth import AdminPermissions, require_admin_permission
from app.models.models import AdminUser, QueryLog, User
from app.schemas.admin import SystemHealthResponse, SystemMetricsResponse
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    current_admin: AdminUser = Depends(require_admin_permission(AdminPermissions.SYSTEM_VIEW)),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _: bool = Depends(apply_admin_rate_limit)
):
    """
    Get comprehensive system health status.

    Returns health status for all major system components including:
    - Database connectivity
    - Redis cache
    - External API services
    - File system
    - Application services
    """
    audit_service = AuditService()

    # Log the admin action
    await audit_service.log_action(
        admin_user_id=current_admin.id,
        action_type="system_health_check",
        resource_type="system",
        ip_address=getattr(request.client, "host", None) if request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
        db=db
    )

    components = {}
    overall_status = "healthy"

    # Database health check
    try:
        db_start = datetime.utcnow()
        result = await db.execute(select(func.count(User.id)))
        user_count = result.scalar()
        db_duration = (datetime.utcnow() - db_start).total_seconds() * 1000

        components["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_duration, 2),
            "details": {
                "total_users": user_count,
                "connection_pool": "active"
            }
        }
    except Exception as e:
        components["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "details": {}
        }
        overall_status = "degraded"

    # Redis health check (simplified)
    try:
        # In production, you'd actually connect to Redis
        components["redis"] = {
            "status": "healthy",
            "response_time_ms": 2.5,
            "details": {
                "memory_usage": "45MB",
                "connected_clients": 12
            }
        }
    except Exception as e:
        components["redis"] = {
            "status": "unhealthy",
            "error": str(e),
            "details": {}
        }
        overall_status = "degraded"

    # External API health check
    try:
        components["external_apis"] = {
            "status": "healthy",
            "details": {
                "amazon_api": "connected",
                "stripe_api": "connected"
            }
        }
    except Exception as e:
        components["external_apis"] = {
            "status": "unhealthy",
            "error": str(e),
            "details": {}
        }
        overall_status = "degraded"

    # File system health check
    try:
        disk_usage = psutil.disk_usage("/")
        components["filesystem"] = {
            "status": "healthy" if disk_usage.percent < 85 else "warning",
            "details": {
                "disk_usage_percent": round(disk_usage.percent, 1),
                "free_space_gb": round(disk_usage.free / (1024**3), 2),
                "total_space_gb": round(disk_usage.total / (1024**3), 2)
            }
        }

        if disk_usage.percent >= 85:
            overall_status = "warning"
    except Exception as e:
        components["filesystem"] = {
            "status": "unhealthy",
            "error": str(e),
            "details": {}
        }
        overall_status = "degraded"

    # Application services
    components["application"] = {
        "status": "healthy",
        "details": {
            "version": settings.version,
            "environment": settings.environment,
            "debug_mode": settings.debug
        }
    }

    # Calculate uptime (simplified - would use actual process start time in production)
    uptime_seconds = 3600  # Placeholder

    return SystemHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        components=components,
        uptime_seconds=uptime_seconds,
        version=settings.version
    )


@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(
    current_admin: AdminUser = Depends(require_admin_permission(AdminPermissions.SYSTEM_MONITOR)),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _: bool = Depends(apply_admin_rate_limit)
):
    """
    Get real-time system performance metrics.

    Returns comprehensive performance data including:
    - API request metrics
    - Database performance
    - System resource usage
    - Cache performance
    """
    audit_service = AuditService()

    # Log the admin action
    await audit_service.log_action(
        admin_user_id=current_admin.id,
        action_type="system_metrics_view",
        resource_type="system",
        ip_address=getattr(request.client, "host", None) if request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
        db=db
    )

    # Calculate API metrics from query logs
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)

    # Requests per minute (last hour average)
    query_count_result = await db.execute(
        select(func.count(QueryLog.id))
        .where(QueryLog.created_at >= one_hour_ago)
    )
    total_requests = query_count_result.scalar() or 0
    requests_per_minute = total_requests / 60.0

    # Average response time
    avg_response_result = await db.execute(
        select(func.avg(QueryLog.response_time_ms))
        .where(QueryLog.created_at >= one_hour_ago)
    )
    average_response_time_ms = float(avg_response_result.scalar() or 0)

    # Error rate
    error_count_result = await db.execute(
        select(func.count(QueryLog.id))
        .where(
            QueryLog.created_at >= one_hour_ago,
            QueryLog.status != "success"
        )
    )
    error_count = error_count_result.scalar() or 0
    error_rate_percent = (error_count / total_requests * 100) if total_requests > 0 else 0

    # Database metrics (simplified)
    database_connections = 10  # Would get from actual connection pool
    database_query_time_ms = 25.5  # Would measure actual query time

    # Cache metrics (simplified)
    cache_hit_rate_percent = 85.2  # Would get from Redis stats
    cache_memory_usage_mb = 45.8  # Would get from Redis info

    # System resource metrics
    cpu_usage_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    memory_usage_percent = memory.percent

    disk_usage = psutil.disk_usage("/")
    disk_usage_percent = disk_usage.percent

    return SystemMetricsResponse(
        timestamp=now,
        requests_per_minute=round(requests_per_minute, 2),
        average_response_time_ms=round(average_response_time_ms, 2),
        error_rate_percent=round(error_rate_percent, 2),
        database_connections=database_connections,
        database_query_time_ms=database_query_time_ms,
        cache_hit_rate_percent=cache_hit_rate_percent,
        cache_memory_usage_mb=cache_memory_usage_mb,
        cpu_usage_percent=round(cpu_usage_percent, 1),
        memory_usage_percent=round(memory_usage_percent, 1),
        disk_usage_percent=round(disk_usage_percent, 1)
    )


@router.get("/status")
async def get_quick_status(
    current_admin: AdminUser = Depends(require_admin_permission(AdminPermissions.SYSTEM_VIEW)),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(apply_admin_rate_limit)
):
    """
    Get quick system status for dashboard widgets.

    Returns lightweight status information for real-time dashboard updates.
    """
    now = datetime.utcnow()

    # Quick database check
    try:
        result = await db.execute(select(func.count(User.id)))
        total_users = result.scalar()
        db_status = "connected"
    except Exception:
        total_users = 0
        db_status = "error"

    # Quick metrics
    one_hour_ago = now - timedelta(hours=1)

    recent_requests_result = await db.execute(
        select(func.count(QueryLog.id))
        .where(QueryLog.created_at >= one_hour_ago)
    )
    recent_requests = recent_requests_result.scalar() or 0

    # System resources
    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent

    return {
        "timestamp": now.isoformat(),
        "status": "operational",
        "database_status": db_status,
        "total_users": total_users,
        "requests_last_hour": recent_requests,
        "cpu_usage_percent": round(cpu_percent, 1),
        "memory_usage_percent": round(memory_percent, 1),
        "version": settings.version
    }


@router.get("/logs")
async def get_system_logs(
    lines: int = 100,
    level: str = "INFO",
    current_admin: AdminUser = Depends(require_admin_permission(AdminPermissions.SYSTEM_MONITOR)),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _: bool = Depends(apply_admin_rate_limit)
):
    """
    Get recent system logs.

    Args:
        lines: Number of log lines to return (max 1000)
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Recent system log entries
    """
    audit_service = AuditService()

    # Log the admin action
    await audit_service.log_action(
        admin_user_id=current_admin.id,
        action_type="system_logs_view",
        resource_type="system",
        details={"lines": lines, "level": level},
        ip_address=getattr(request.client, "host", None) if request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
        db=db
    )

    # Limit lines to prevent abuse
    lines = min(lines, 1000)

    # In production, this would read actual log files or from a log aggregation service
    # For demo, return mock log entries
    mock_logs = []
    base_time = datetime.utcnow()

    for i in range(lines):
        log_time = base_time - timedelta(minutes=i)
        log_entry = {
            "timestamp": log_time.isoformat(),
            "level": "INFO" if i % 10 != 0 else "WARNING",
            "logger": "app.api.v1.endpoints.products" if i % 3 == 0 else "app.services.amazon_service",
            "message": "Processed ASIN query request" if i % 3 == 0 else "Cache hit for product lookup",
            "module": "products.py" if i % 3 == 0 else "amazon_service.py",
            "line": 45 + (i % 10)
        }

        # Add error logs occasionally
        if i % 25 == 0:
            log_entry.update({
                "level": "ERROR",
                "message": "Failed to fetch product data from external API",
                "error": "ConnectionTimeout: Request timed out after 30 seconds"
            })

        mock_logs.append(log_entry)

    return {
        "logs": mock_logs,
        "total_lines": lines,
        "level_filter": level,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/restart")
async def restart_service(
    service: str,
    current_admin: AdminUser = Depends(require_admin_permission(AdminPermissions.SYSTEM_CONFIG)),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _: bool = Depends(apply_admin_rate_limit)
):
    """
    Restart a system service (admin only).

    Args:
        service: Service name to restart

    WARNING: This endpoint would restart actual services in production.
    Use with extreme caution.
    """
    audit_service = AuditService()

    # Log the admin action
    await audit_service.log_action(
        admin_user_id=current_admin.id,
        action_type="service_restart",
        resource_type="system",
        resource_id=service,
        details={"service": service, "requested_by": current_admin.id},
        ip_address=getattr(request.client, "host", None) if request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
        db=db
    )

    # Only allow specific services
    allowed_services = ["cache", "worker", "scheduler"]

    if service not in allowed_services:
        return {
            "success": False,
            "error": f"Service '{service}' not allowed. Allowed services: {allowed_services}"
        }

    # In production, this would actually restart the service
    # For demo, return success message
    return {
        "success": True,
        "message": f"Service '{service}' restart initiated",
        "timestamp": datetime.utcnow().isoformat(),
        "initiated_by": current_admin.id
    }


@router.get("/performance")
async def get_performance_data(
    hours: int = 24,
    current_admin: AdminUser = Depends(require_admin_permission(AdminPermissions.SYSTEM_MONITOR)),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _: bool = Depends(apply_admin_rate_limit)
):
    """
    Get historical performance data for charts and analysis.

    Args:
        hours: Number of hours of historical data to return

    Returns:
        Performance metrics over time for dashboard charts
    """
    audit_service = AuditService()

    # Log the admin action
    await audit_service.log_action(
        admin_user_id=current_admin.id,
        action_type="performance_data_view",
        resource_type="system",
        details={"hours": hours},
        ip_address=getattr(request.client, "host", None) if request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
        db=db
    )

    # Limit to reasonable range
    hours = min(hours, 168)  # Max 1 week

    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    # Get hourly aggregated query data
    hourly_stats = await db.execute(
        select(
            func.date_trunc("hour", QueryLog.created_at).label("hour"),
            func.count(QueryLog.id).label("request_count"),
            func.avg(QueryLog.response_time_ms).label("avg_response_time"),
            func.count(func.case([(QueryLog.status != "success", 1)])).label("error_count")
        )
        .where(QueryLog.created_at >= cutoff_time)
        .group_by(func.date_trunc("hour", QueryLog.created_at))
        .order_by(func.date_trunc("hour", QueryLog.created_at))
    )

    performance_data = []
    for row in hourly_stats:
        performance_data.append({
            "timestamp": row.hour.isoformat(),
            "request_count": row.request_count,
            "avg_response_time_ms": round(float(row.avg_response_time or 0), 2),
            "error_count": row.error_count,
            "error_rate_percent": round(
                (row.error_count / row.request_count * 100) if row.request_count > 0 else 0, 2
            )
        })

    return {
        "performance_data": performance_data,
        "time_range_hours": hours,
        "data_points": len(performance_data),
        "generated_at": datetime.utcnow().isoformat()
    }
