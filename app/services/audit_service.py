"""
Audit logging service for comprehensive admin action tracking.
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import AdminAction, AdminUser, User
from app.schemas.admin import (
    AdminUserResponse,
    AuditLogResponse,
    PaginatedAuditLogsResponse,
    UserResponse,
)


class AuditService:
    """Service for audit logging and retrieval."""

    async def log_action(
        self,
        admin_user_id: str,
        action_type: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        db: AsyncSession = None
    ) -> AdminAction:
        """
        Log an admin action for audit purposes.

        Args:
            admin_user_id: ID of admin user performing action
            action_type: Type of action performed
            resource_type: Type of resource affected
            resource_id: ID of specific resource (optional)
            details: Additional action details
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether action was successful
            error_message: Error message if action failed
            duration_ms: Action duration in milliseconds
            db: Database session

        Returns:
            Created AdminAction record
        """
        # Create audit log entry
        audit_log = AdminAction(
            admin_user_id=admin_user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms
        )

        try:
            db.add(audit_log)
            await db.commit()
            await db.refresh(audit_log)
        except Exception as e:
            # If audit logging fails, rollback and continue without audit log
            # This prevents audit logging issues from breaking the main functionality
            await db.rollback()
            print(f"Warning: Failed to log audit action: {str(e)}")
            # Create a minimal audit log object for return
            audit_log.id = None
            return audit_log

        return audit_log

    async def get_audit_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        admin_user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        success_filter: Optional[bool] = None,
        search: Optional[str] = None,
        db: AsyncSession = None
    ) -> PaginatedAuditLogsResponse:
        """
        Get paginated audit logs with filtering.

        Args:
            skip: Number of records to skip
            limit: Number of records to return
            admin_user_id: Filter by admin user
            action_type: Filter by action type
            resource_type: Filter by resource type
            resource_id: Filter by specific resource
            start_date: Start date filter
            end_date: End date filter
            success_filter: Filter by success status
            search: Search in action details
            db: Database session

        Returns:
            PaginatedAuditLogsResponse with logs and metadata
        """
        # Build base query with relationships
        query = select(AdminAction).options(
            selectinload(AdminAction.admin_user)
            .selectinload(AdminUser.user)
        )
        count_query = select(func.count(AdminAction.id))

        # Build filter conditions
        conditions = []

        if admin_user_id:
            conditions.append(AdminAction.admin_user_id == admin_user_id)

        if action_type:
            conditions.append(AdminAction.action_type == action_type)

        if resource_type:
            conditions.append(AdminAction.resource_type == resource_type)

        if resource_id:
            conditions.append(AdminAction.resource_id == resource_id)

        if start_date:
            conditions.append(AdminAction.created_at >= start_date)

        if end_date:
            conditions.append(AdminAction.created_at <= end_date)

        if success_filter is not None:
            conditions.append(AdminAction.success == success_filter)

        if search:
            # Search in details JSON and error message
            search_term = f"%{search.lower()}%"
            conditions.append(
                or_(
                    func.lower(func.cast(AdminAction.details, text)).contains(search_term),
                    func.lower(AdminAction.error_message).contains(search_term),
                    func.lower(AdminAction.action_type).contains(search_term)
                )
            )

        # Apply filters
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Apply ordering and pagination
        query = query.order_by(desc(AdminAction.created_at)).offset(skip).limit(limit)

        # Execute queries
        result = await db.execute(query)
        logs = result.scalars().all()

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # Transform to response format
        log_responses = []
        for log in logs:
            # Build admin user response
            admin_user_response = None
            if log.admin_user and log.admin_user.user:
                user_response = UserResponse(
                    id=log.admin_user.user.id,
                    email=log.admin_user.user.email,
                    full_name=log.admin_user.user.full_name,
                    is_active=log.admin_user.user.is_active,
                    is_verified=log.admin_user.user.is_verified,
                    credit_balance=log.admin_user.user.credit_balance,
                    created_at=log.admin_user.user.created_at,
                    updated_at=log.admin_user.user.updated_at
                )

                admin_user_response = AdminUserResponse(
                    id=log.admin_user.id,
                    user_id=log.admin_user.user_id,
                    admin_role=log.admin_user.admin_role,
                    permissions=log.admin_user.permissions,
                    is_active=log.admin_user.is_active,
                    created_at=log.admin_user.created_at,
                    updated_at=log.admin_user.updated_at,
                    user=user_response
                )

            log_responses.append(AuditLogResponse(
                id=log.id,
                admin_user_id=log.admin_user_id,
                action_type=log.action_type,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                details=log.details,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                created_at=log.created_at,
                success=log.success,
                error_message=log.error_message,
                duration_ms=log.duration_ms,
                admin_user=admin_user_response
            ))

        return PaginatedAuditLogsResponse(
            logs=log_responses,
            total=total,
            skip=skip,
            limit=limit,
            has_next=skip + limit < total,
            has_previous=skip > 0
        )

    async def get_action_types(self, db: AsyncSession) -> list[str]:
        """Get list of all action types in the audit log."""
        result = await db.execute(
            select(AdminAction.action_type)
            .distinct()
            .order_by(AdminAction.action_type)
        )
        return [row[0] for row in result.fetchall()]

    async def get_resource_types(self, db: AsyncSession) -> list[str]:
        """Get list of all resource types in the audit log."""
        result = await db.execute(
            select(AdminAction.resource_type)
            .distinct()
            .order_by(AdminAction.resource_type)
        )
        return [row[0] for row in result.fetchall()]

    async def get_audit_stats(
        self,
        admin_user_id: Optional[str] = None,
        days: int = 30,
        db: AsyncSession = None
    ) -> dict[str, Any]:
        """
        Get audit statistics for a time period.

        Args:
            admin_user_id: Optional admin user to filter by
            days: Number of days to analyze
            db: Database session

        Returns:
            Dictionary with audit statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Base conditions
        conditions = [AdminAction.created_at >= cutoff_date]
        if admin_user_id:
            conditions.append(AdminAction.admin_user_id == admin_user_id)

        # Total actions
        total_result = await db.execute(
            select(func.count(AdminAction.id))
            .where(and_(*conditions))
        )
        total_actions = total_result.scalar()

        # Success rate
        success_result = await db.execute(
            select(
                func.count(AdminAction.id).label("total"),
                func.sum(func.case([(AdminAction.success == True, 1)], else_=0)).label("successful")
            )
            .where(and_(*conditions))
        )
        success_data = success_result.first()
        success_rate = (success_data.successful / success_data.total * 100) if success_data.total > 0 else 0

        # Actions by type
        type_result = await db.execute(
            select(
                AdminAction.action_type,
                func.count(AdminAction.id).label("count")
            )
            .where(and_(*conditions))
            .group_by(AdminAction.action_type)
            .order_by(desc(func.count(AdminAction.id)))
        )
        actions_by_type = {row.action_type: row.count for row in type_result}

        # Actions by resource type
        resource_result = await db.execute(
            select(
                AdminAction.resource_type,
                func.count(AdminAction.id).label("count")
            )
            .where(and_(*conditions))
            .group_by(AdminAction.resource_type)
            .order_by(desc(func.count(AdminAction.id)))
        )
        actions_by_resource = {row.resource_type: row.count for row in resource_result}

        # Daily activity (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        daily_conditions = conditions + [AdminAction.created_at >= seven_days_ago]

        daily_result = await db.execute(
            select(
                func.date_trunc("day", AdminAction.created_at).label("day"),
                func.count(AdminAction.id).label("count")
            )
            .where(and_(*daily_conditions))
            .group_by(func.date_trunc("day", AdminAction.created_at))
            .order_by(func.date_trunc("day", AdminAction.created_at))
        )

        daily_activity = {}
        for row in daily_result:
            day_key = row.day.strftime("%Y-%m-%d")
            daily_activity[day_key] = row.count

        # Top admin users (if not filtering by specific admin)
        top_admins = {}
        if not admin_user_id:
            admin_result = await db.execute(
                select(
                    AdminAction.admin_user_id,
                    func.count(AdminAction.id).label("count")
                )
                .where(and_(*conditions))
                .group_by(AdminAction.admin_user_id)
                .order_by(desc(func.count(AdminAction.id)))
                .limit(10)
            )

            for row in admin_result:
                # Get admin user details
                admin_detail = await db.execute(
                    select(AdminUser, User)
                    .join(User)
                    .where(AdminUser.id == row.admin_user_id)
                )
                admin_data = admin_detail.first()

                if admin_data:
                    admin_user, user = admin_data
                    top_admins[user.email] = row.count

        # Failed actions analysis
        failed_result = await db.execute(
            select(
                AdminAction.action_type,
                AdminAction.error_message,
                func.count(AdminAction.id).label("count")
            )
            .where(and_(
                *conditions,
                AdminAction.success == False
            ))
            .group_by(AdminAction.action_type, AdminAction.error_message)
            .order_by(desc(func.count(AdminAction.id)))
            .limit(10)
        )

        failed_actions = []
        for row in failed_result:
            failed_actions.append({
                "action_type": row.action_type,
                "error_message": row.error_message,
                "count": row.count
            })

        return {
            "time_period_days": days,
            "total_actions": total_actions,
            "success_rate_percent": round(success_rate, 2),
            "actions_by_type": actions_by_type,
            "actions_by_resource": actions_by_resource,
            "daily_activity": daily_activity,
            "top_admin_users": top_admins,
            "failed_actions": failed_actions
        }

    async def cleanup_old_audit_logs(
        self,
        retention_days: int = 365,
        batch_size: int = 1000,
        db: AsyncSession = None
    ) -> int:
        """
        Clean up old audit logs beyond retention period.

        Args:
            retention_days: Number of days to retain logs
            batch_size: Number of records to delete per batch
            db: Database session

        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Count total records to delete
        count_result = await db.execute(
            select(func.count(AdminAction.id))
            .where(AdminAction.created_at < cutoff_date)
        )
        total_to_delete = count_result.scalar()

        if total_to_delete == 0:
            return 0

        # Delete in batches to avoid long-running transactions
        deleted_count = 0

        while deleted_count < total_to_delete:
            # Delete a batch
            delete_result = await db.execute(
                text("""
                    DELETE FROM admin_actions
                    WHERE id IN (
                        SELECT id FROM admin_actions
                        WHERE created_at < :cutoff_date
                        LIMIT :batch_size
                    )
                """),
                {"cutoff_date": cutoff_date, "batch_size": batch_size}
            )

            batch_deleted = delete_result.rowcount
            if batch_deleted == 0:
                break

            deleted_count += batch_deleted
            await db.commit()

            # Small delay to avoid overwhelming the database
            await asyncio.sleep(0.1)

        return deleted_count

    def create_audit_context(self) -> "AuditContext":
        """Create an audit context for tracking action performance."""
        return AuditContext(self)


class AuditContext:
    """Context manager for tracking admin action performance and automatic logging."""

    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service
        self.start_time = None
        self.admin_user_id = None
        self.action_type = None
        self.resource_type = None
        self.resource_id = None
        self.details = None
        self.ip_address = None
        self.user_agent = None
        self.db = None
        self.success = True
        self.error_message = None

    def setup(
        self,
        admin_user_id: str,
        action_type: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        db: AsyncSession = None
    ):
        """Setup audit context parameters."""
        self.admin_user_id = admin_user_id
        self.action_type = action_type
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.details = details or {}
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.db = db
        return self

    async def __aenter__(self):
        """Start timing the action."""
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Log the action with timing information."""
        if self.start_time is not None:
            duration_ms = int((time.time() - self.start_time) * 1000)
        else:
            duration_ms = None

        # Determine success based on exception
        if exc_type is not None:
            self.success = False
            self.error_message = str(exc_val) if exc_val else "Unknown error"

        # Add timing to details
        if duration_ms is not None:
            self.details["duration_ms"] = duration_ms

        # Log the action
        if self.db and self.admin_user_id:
            await self.audit_service.log_action(
                admin_user_id=self.admin_user_id,
                action_type=self.action_type,
                resource_type=self.resource_type,
                resource_id=self.resource_id,
                details=self.details,
                ip_address=self.ip_address,
                user_agent=self.user_agent,
                success=self.success,
                error_message=self.error_message,
                duration_ms=duration_ms,
                db=self.db
            )

    def add_detail(self, key: str, value: Any):
        """Add additional detail to the audit log."""
        if self.details is None:
            self.details = {}
        self.details[key] = value

    def mark_failure(self, error_message: str):
        """Mark the action as failed with an error message."""
        self.success = False
        self.error_message = error_message
