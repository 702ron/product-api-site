"""
Core admin business logic and service functions.
"""
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.models.models import AdminUser, CreditTransaction, QueryLog, User
from app.schemas.admin import (
    AdminUserDetailResponse,
    AdminUserListResponse,
    PaginatedUsersResponse,
    UserStatsResponse,
)


class AdminService:
    """Service class for admin operations."""

    async def get_users_paginated(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        role_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        db: AsyncSession = None
    ) -> PaginatedUsersResponse:
        """
        Get paginated list of users with filtering and search.

        Args:
            skip: Number of records to skip
            limit: Number of records to return
            search: Search term for email/name
            role_filter: Filter by admin role
            status_filter: Filter by user status
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            db: Database session

        Returns:
            PaginatedUsersResponse with users and metadata
        """
        # Build base query
        query = select(User).outerjoin(AdminUser)
        count_query = select(func.count(User.id)).outerjoin(AdminUser)

        # Apply filters
        conditions = []

        # Search filter
        if search:
            search_term = f"%{search.lower()}%"
            conditions.append(
                or_(
                    func.lower(User.email).contains(search_term),
                    func.lower(User.full_name).contains(search_term)
                )
            )

        # Role filter
        if role_filter:
            if role_filter == "regular":
                conditions.append(AdminUser.id.is_(None))
            else:
                conditions.append(AdminUser.admin_role == role_filter)

        # Status filter
        if status_filter:
            if status_filter == "active":
                conditions.append(User.is_active == True)
            elif status_filter == "inactive":
                conditions.append(User.is_active == False)
            elif status_filter == "verified":
                conditions.append(User.is_verified == True)
            elif status_filter == "unverified":
                conditions.append(User.is_verified == False)

        # Apply conditions
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Apply sorting
        sort_column = getattr(User, sort_by, User.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        # Execute queries
        result = await db.execute(query.options(selectinload(User.admin_profile)))
        users = result.scalars().all()

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # Transform to response format
        user_responses = []
        for user in users:
            admin_role = None
            admin_permissions = None

            # admin_profile is a list, get the first active admin profile
            if user.admin_profile:
                # Get the first active admin profile
                active_profile = next((p for p in user.admin_profile if p.is_active), None)
                if active_profile:
                    admin_role = active_profile.admin_role
                    # Ensure permissions are in dict format for API response
                    raw_permissions = active_profile.permissions
                    if isinstance(raw_permissions, list):
                        # Convert list format to dict format
                        admin_permissions = {"additional": raw_permissions}
                    elif isinstance(raw_permissions, dict):
                        admin_permissions = raw_permissions
                    else:
                        admin_permissions = None

            user_responses.append(AdminUserListResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                credit_balance=user.credit_balance,
                created_at=user.created_at,
                admin_role=admin_role,
                admin_permissions=admin_permissions
            ))

        return PaginatedUsersResponse(
            users=user_responses,
            total=total,
            skip=skip,
            limit=limit,
            has_next=skip + limit < total,
            has_previous=skip > 0
        )

    async def get_user_by_id(self, user_id: str, db: AsyncSession) -> Optional[User]:
        """Get user by ID."""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_detail(self, user_id: str, db: AsyncSession) -> Optional[AdminUserDetailResponse]:
        """
        Get detailed user information including activity stats.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            AdminUserDetailResponse or None if user not found
        """
        # Get user with admin profile
        user_result = await db.execute(
            select(User)
            .options(selectinload(User.admin_profile))
            .where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return None

        # Get activity statistics
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)

        # Total queries
        total_queries_result = await db.execute(
            select(func.count(QueryLog.id)).where(QueryLog.user_id == user_id)
        )
        total_queries = total_queries_result.scalar() or 0

        # Queries last 30 days
        recent_queries_result = await db.execute(
            select(func.count(QueryLog.id))
            .where(and_(
                QueryLog.user_id == user_id,
                QueryLog.created_at >= thirty_days_ago
            ))
        )
        queries_last_30_days = recent_queries_result.scalar() or 0

        # Total credits spent
        credits_spent_result = await db.execute(
            select(func.sum(CreditTransaction.amount))
            .where(and_(
                CreditTransaction.user_id == user_id,
                CreditTransaction.transaction_type == "usage",
                CreditTransaction.amount < 0
            ))
        )
        total_credits_spent = abs(credits_spent_result.scalar() or 0)

        # Credits spent last 30 days
        recent_credits_result = await db.execute(
            select(func.sum(CreditTransaction.amount))
            .where(and_(
                CreditTransaction.user_id == user_id,
                CreditTransaction.transaction_type == "usage",
                CreditTransaction.amount < 0,
                CreditTransaction.created_at >= thirty_days_ago
            ))
        )
        credits_spent_last_30_days = abs(recent_credits_result.scalar() or 0)

        # Total credits purchased
        credits_purchased_result = await db.execute(
            select(func.sum(CreditTransaction.amount))
            .where(and_(
                CreditTransaction.user_id == user_id,
                CreditTransaction.transaction_type == "purchase",
                CreditTransaction.amount > 0
            ))
        )
        total_credits_purchased = credits_purchased_result.scalar() or 0

        # Last activity (most recent query)
        last_activity_result = await db.execute(
            select(QueryLog.created_at)
            .where(QueryLog.user_id == user_id)
            .order_by(desc(QueryLog.created_at))
            .limit(1)
        )
        last_activity = last_activity_result.scalar_one_or_none()

        # Build response
        admin_role = None
        admin_permissions = None
        if user.admin_profile:
            # admin_profile is a list, get the first active admin profile
            active_profile = next((p for p in user.admin_profile if p.is_active), None)
            if active_profile:
                admin_role = active_profile.admin_role
                # Ensure permissions are in dict format for API response
                raw_permissions = active_profile.permissions
                if isinstance(raw_permissions, list):
                    # Convert list format to dict format
                    admin_permissions = {"additional": raw_permissions}
                elif isinstance(raw_permissions, dict):
                    admin_permissions = raw_permissions
                else:
                    admin_permissions = None

        return AdminUserDetailResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            credit_balance=user.credit_balance,
            created_at=user.created_at,
            updated_at=user.updated_at,
            admin_role=admin_role,
            admin_permissions=admin_permissions,
            total_queries=total_queries,
            total_credits_spent=total_credits_spent,
            total_credits_purchased=total_credits_purchased,
            last_activity=last_activity,
            queries_last_30_days=queries_last_30_days,
            credits_spent_last_30_days=credits_spent_last_30_days
        )

    async def update_user_status(
        self,
        user_id: str,
        is_active: bool,
        admin_user_id: str,
        db: AsyncSession
    ) -> User:
        """
        Update user active status.

        Args:
            user_id: User ID to update
            is_active: New active status
            admin_user_id: Admin performing the action
            db: Database session

        Returns:
            Updated User object

        Raises:
            ResourceNotFoundError: If user not found
        """
        user = await self.get_user_by_id(user_id, db)
        if not user:
            raise ResourceNotFoundError("User not found", "user", user_id)

        user.is_active = is_active
        user.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)

        return user

    async def adjust_user_credits(
        self,
        user_id: str,
        amount: int,
        reason: str,
        admin_user_id: str,
        db: AsyncSession
    ) -> CreditTransaction:
        """
        Adjust user credit balance.

        Args:
            user_id: User ID
            amount: Amount to adjust (positive to add, negative to subtract)
            reason: Reason for adjustment
            admin_user_id: Admin performing the action
            db: Database session

        Returns:
            Created CreditTransaction

        Raises:
            ResourceNotFoundError: If user not found
            ValidationError: If adjustment would result in negative balance
        """
        user = await self.get_user_by_id(user_id, db)
        if not user:
            raise ResourceNotFoundError("User not found", "user", user_id)

        # Check if adjustment would result in negative balance
        new_balance = user.credit_balance + amount
        if new_balance < 0:
            raise ValidationError(
                f"Credit adjustment would result in negative balance. "
                f"Current: {user.credit_balance}, Adjustment: {amount}, "
                f"Resulting: {new_balance}"
            )

        # Update user balance
        user.credit_balance = new_balance
        user.updated_at = datetime.utcnow()

        # Create transaction record
        transaction = CreditTransaction(
            user_id=user_id,
            amount=amount,
            transaction_type="adjustment",
            description=f"Admin adjustment: {reason}",
            extra_data={"admin_user_id": admin_user_id, "reason": reason}
        )

        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        return transaction

    async def get_user_activity(
        self,
        user_id: str,
        days: int = 30,
        db: AsyncSession = None
    ) -> list[dict[str, Any]]:
        """
        Get user activity history.

        Args:
            user_id: User ID
            days: Number of days to look back
            db: Database session

        Returns:
            List of activity events
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        activity = []

        # Get recent queries
        query_result = await db.execute(
            select(QueryLog)
            .where(and_(
                QueryLog.user_id == user_id,
                QueryLog.created_at >= cutoff_date
            ))
            .order_by(desc(QueryLog.created_at))
            .limit(100)
        )
        queries = query_result.scalars().all()

        for query in queries:
            activity.append({
                "type": "query",
                "timestamp": query.created_at,
                "details": {
                    "query_type": query.query_type,
                    "credits_deducted": query.credits_deducted,
                    "status": query.status,
                    "endpoint": query.endpoint
                }
            })

        # Get recent transactions
        transaction_result = await db.execute(
            select(CreditTransaction)
            .where(and_(
                CreditTransaction.user_id == user_id,
                CreditTransaction.created_at >= cutoff_date
            ))
            .order_by(desc(CreditTransaction.created_at))
            .limit(50)
        )
        transactions = transaction_result.scalars().all()

        for transaction in transactions:
            activity.append({
                "type": "transaction",
                "timestamp": transaction.created_at,
                "details": {
                    "amount": transaction.amount,
                    "transaction_type": transaction.transaction_type,
                    "description": transaction.description
                }
            })

        # Sort by timestamp
        activity.sort(key=lambda x: x["timestamp"], reverse=True)

        return activity

    async def get_user_stats(self, user_id: str, db: AsyncSession) -> Optional[UserStatsResponse]:
        """
        Get comprehensive user statistics.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            UserStatsResponse or None if user not found
        """
        user = await self.get_user_by_id(user_id, db)
        if not user:
            return None

        # Query statistics aggregations
        now = datetime.utcnow()

        # Total queries and success rate
        query_stats = await db.execute(
            select(
                func.count(QueryLog.id).label("total"),
                func.sum(func.case([(QueryLog.status == "success", 1)], else_=0)).label("successful"),
                func.sum(func.case([(QueryLog.status != "success", 1)], else_=0)).label("failed"),
                func.avg(QueryLog.response_time_ms).label("avg_response_time")
            ).where(QueryLog.user_id == user_id)
        )
        query_result = query_stats.first()

        # Credit statistics
        credit_stats = await db.execute(
            select(
                func.sum(func.case([
                    (and_(CreditTransaction.transaction_type == "purchase", CreditTransaction.amount > 0),
                     CreditTransaction.amount)
                ], else_=0)).label("purchased"),
                func.sum(func.case([
                    (and_(CreditTransaction.transaction_type == "usage", CreditTransaction.amount < 0),
                     func.abs(CreditTransaction.amount))
                ], else_=0)).label("spent")
            ).where(CreditTransaction.user_id == user_id)
        )
        credit_result = credit_stats.first()

        # Monthly breakdowns
        six_months_ago = now - timedelta(days=180)

        # Queries by month
        monthly_queries = await db.execute(
            select(
                func.date_trunc("month", QueryLog.created_at).label("month"),
                func.count(QueryLog.id).label("count")
            )
            .where(and_(
                QueryLog.user_id == user_id,
                QueryLog.created_at >= six_months_ago
            ))
            .group_by(func.date_trunc("month", QueryLog.created_at))
            .order_by(func.date_trunc("month", QueryLog.created_at))
        )

        queries_by_month = {}
        for row in monthly_queries:
            month_key = row.month.strftime("%Y-%m")
            queries_by_month[month_key] = row.count

        # Credits spent by month
        monthly_credits = await db.execute(
            select(
                func.date_trunc("month", CreditTransaction.created_at).label("month"),
                func.sum(func.abs(CreditTransaction.amount)).label("amount")
            )
            .where(and_(
                CreditTransaction.user_id == user_id,
                CreditTransaction.transaction_type == "usage",
                CreditTransaction.amount < 0,
                CreditTransaction.created_at >= six_months_ago
            ))
            .group_by(func.date_trunc("month", CreditTransaction.created_at))
            .order_by(func.date_trunc("month", CreditTransaction.created_at))
        )

        credits_by_month = {}
        for row in monthly_credits:
            month_key = row.month.strftime("%Y-%m")
            credits_by_month[month_key] = int(row.amount or 0)

        # Query types breakdown
        query_types_result = await db.execute(
            select(
                QueryLog.query_type,
                func.count(QueryLog.id).label("count")
            )
            .where(QueryLog.user_id == user_id)
            .group_by(QueryLog.query_type)
        )

        query_types = {}
        for row in query_types_result:
            query_types[row.query_type] = row.count

        # Last login and query
        last_query_result = await db.execute(
            select(QueryLog.created_at)
            .where(QueryLog.user_id == user_id)
            .order_by(desc(QueryLog.created_at))
            .limit(1)
        )
        last_query = last_query_result.scalar_one_or_none()

        # Account age
        account_age_days = (now - user.created_at).days

        return UserStatsResponse(
            user_id=user_id,
            email=user.email,
            total_queries=query_result.total or 0,
            successful_queries=query_result.successful or 0,
            failed_queries=query_result.failed or 0,
            total_credits_purchased=int(credit_result.purchased or 0),
            total_credits_spent=int(credit_result.spent or 0),
            current_credit_balance=user.credit_balance,
            queries_by_month=queries_by_month,
            credits_spent_by_month=credits_by_month,
            query_types=query_types,
            average_response_time_ms=float(query_result.avg_response_time or 0),
            account_age_days=account_age_days,
            last_login=None,  # Would need session tracking for this
            last_query=last_query
        )

    async def soft_delete_user(
        self,
        user_id: str,
        reason: str,
        admin_user_id: str,
        db: AsyncSession
    ) -> None:
        """
        Soft delete a user (mark as inactive and store deletion info).

        Args:
            user_id: User ID to delete
            reason: Reason for deletion
            admin_user_id: Admin performing the action
            db: Database session

        Raises:
            ResourceNotFoundError: If user not found
        """
        user = await self.get_user_by_id(user_id, db)
        if not user:
            raise ResourceNotFoundError("User not found", "user", user_id)

        # Mark user as inactive
        user.is_active = False
        user.updated_at = datetime.utcnow()

        # Store deletion information in extra data or separate table
        # For now, we'll use a credit transaction to log the deletion
        deletion_transaction = CreditTransaction(
            user_id=user_id,
            amount=0,
            transaction_type="adjustment",
            description=f"Account soft deleted: {reason}",
            extra_data={
                "action": "soft_delete",
                "admin_user_id": admin_user_id,
                "reason": reason,
                "deleted_at": datetime.utcnow().isoformat()
            }
        )

        db.add(deletion_transaction)
        await db.commit()

    async def create_admin_user(
        self,
        user_id: str,
        admin_role: str,
        permissions: Optional[list[str]] = None,
        created_by: str = None,
        db: AsyncSession = None
    ) -> AdminUser:
        """
        Create an admin user.

        Args:
            user_id: Regular user ID
            admin_role: Admin role to assign
            permissions: Custom permissions
            created_by: Admin user who created this admin
            db: Database session

        Returns:
            Created AdminUser

        Raises:
            ResourceNotFoundError: If user not found
            ValidationError: If user already has admin role
        """
        # Check if user exists
        user = await self.get_user_by_id(user_id, db)
        if not user:
            raise ResourceNotFoundError("User not found", "user", user_id)

        # Check if user already has admin role
        existing_admin = await db.execute(
            select(AdminUser).where(AdminUser.user_id == user_id)
        )
        if existing_admin.scalar_one_or_none():
            raise ValidationError("User already has admin role")

        # Create admin user
        admin_user = AdminUser(
            user_id=user_id,
            admin_role=admin_role,
            permissions={"additional": permissions} if permissions else None,
            created_by=created_by
        )

        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)

        return admin_user

    async def revoke_admin_role(
        self,
        user_id: str,
        revoked_by: str,
        db: AsyncSession
    ) -> None:
        """
        Revoke admin role from a user.

        Args:
            user_id: User ID
            revoked_by: Admin user who revoked the role
            db: Database session

        Raises:
            ResourceNotFoundError: If admin user not found
        """
        # Find and delete admin user record
        result = await db.execute(
            select(AdminUser).where(AdminUser.user_id == user_id)
        )
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            raise ResourceNotFoundError("Admin user not found", "admin_user", user_id)

        # Mark as inactive instead of deleting to preserve audit trail
        admin_user.is_active = False
        admin_user.updated_at = datetime.utcnow()

        await db.commit()
