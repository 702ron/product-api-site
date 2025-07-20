"""
Admin user management endpoints.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PaginationParams, apply_admin_rate_limit, get_pagination_params
from app.core.database import get_db
from app.middleware.admin_auth import AdminPermissions, log_security_event, require_admin_permission
from app.models.models import AdminUser, User
from app.schemas.admin import AdminUserDetailResponse, PaginatedUsersResponse, UserStatsResponse
from app.services.admin_service import AdminService
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("/users", response_model=PaginatedUsersResponse)
async def get_users(
    pagination: PaginationParams = Depends(get_pagination_params),
    search: Optional[str] = None,
    role_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_admin: AdminUser = Depends(require_admin_permission(AdminPermissions.USER_VIEW)),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _: bool = Depends(apply_admin_rate_limit)
):
    """
    Get paginated list of users with filtering and search.

    Query parameters:
    - skip: Number of records to skip (default: 0)
    - limit: Number of records to return (default: 50, max: 1000)
    - search: Search in email, full_name fields
    - role_filter: Filter by admin role (super_admin, admin, moderator, viewer)
    - status_filter: Filter by status (active, inactive, verified, unverified)
    - sort_by: Field to sort by (created_at, email, full_name, credit_balance)
    - sort_order: Sort order (asc, desc)
    """
    audit_service = AuditService()

    # Log the admin action
    await audit_service.log_action(
        admin_user_id=current_admin.id,
        action_type="user_list_view",
        resource_type="user",
        details={
            "search": search,
            "role_filter": role_filter,
            "status_filter": status_filter,
            "pagination": {"skip": pagination.skip, "limit": pagination.limit}
        },
        ip_address=getattr(request.client, "host", None) if request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
        db=db
    )

    admin_service = AdminService()
    result = await admin_service.get_users_paginated(
        skip=pagination.skip,
        limit=pagination.limit,
        search=search,
        role_filter=role_filter,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
        db=db
    )

    return result


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
async def get_user_detail(
    user_id: str,
    current_admin: AdminUser = Depends(require_admin_permission(AdminPermissions.USER_VIEW)),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _: bool = Depends(apply_admin_rate_limit)
):
    """Get detailed information about a specific user."""
    audit_service = AuditService()

    # Log the admin action
    await audit_service.log_action(
        admin_user_id=current_admin.id,
        action_type="user_detail_view",
        resource_type="user",
        resource_id=user_id,
        ip_address=getattr(request.client, "host", None) if request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
        db=db
    )

    admin_service = AdminService()
    user_detail = await admin_service.get_user_detail(user_id, db)

    if not user_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user_detail


@router.post("/users/{user_id}/status", response_model=AdminUserDetailResponse)
async def update_user_status(
    user_id: str,
    is_active: bool,
    current_admin: AdminUser = Depends(require_admin_permission(AdminPermissions.USER_UPDATE)),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _: bool = Depends(apply_admin_rate_limit)
):
    """Update user active status."""
    audit_service = AuditService()
    admin_service = AdminService()

    # Get current user state for audit trail
    user = await admin_service.get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    old_status = user.is_active

    # Update user status
    updated_user = await admin_service.update_user_status(
        user_id=user_id,
        is_active=is_active,
        admin_user_id=current_admin.id,
        db=db
    )

    # Log the admin action
    await audit_service.log_action(
        admin_user_id=current_admin.id,
        action_type="user_status_update",
        resource_type="user",
        resource_id=user_id,
        details={
            "old_status": old_status,
            "new_status": is_active,
            "user_email": user.email
        },
        ip_address=getattr(request.client, "host", None) if request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
        db=db
    )

    # Log security event if user was deactivated
    if not is_active and old_status:
        await log_security_event(
            event_type="user_deactivated",
            severity="medium",
            details={
                "user_id": user_id,
                "user_email": user.email,
                "admin_user_id": current_admin.id,
                "reason": "admin_action"
            },
            request=request,
            db=db,
            user_id=user_id,
            admin_user_id=current_admin.id
        )

    return await admin_service.get_user_detail(user_id, db)


@router.post("/users/{user_id}/credits", response_model=AdminUserDetailResponse)
async def adjust_user_credits(
    user_id: str,
    amount: int,
    reason: str,
    current_admin: AdminUser = Depends(require_admin_permission(AdminPermissions.USER_MANAGE)),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _: bool = Depends(apply_admin_rate_limit)
):
    """Adjust user credit balance (positive to add, negative to subtract)."""
    audit_service = AuditService()
    admin_service = AdminService()

    # Get current user state
    user = await admin_service.get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    old_balance = user.credit_balance

    # Adjust credits
    await admin_service.adjust_user_credits(
        user_id=user_id,
        amount=amount,
        reason=reason,
        admin_user_id=current_admin.id,
        db=db
    )

    # Log the admin action
    await audit_service.log_action(
        admin_user_id=current_admin.id,
        action_type="user_credits_adjustment",
        resource_type="user",
        resource_id=user_id,
        details={
            "old_balance": old_balance,
            "adjustment_amount": amount,
            "new_balance": old_balance + amount,
            "reason": reason,
            "user_email": user.email
        },
        ip_address=getattr(request.client, "host", None) if request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
        db=db
    )

    return await admin_service.get_user_detail(user_id, db)


@router.get("/users/{user_id}/activity", response_model=list[dict])
async def get_user_activity(
    user_id: str,
    days: int = 30,
    current_admin: AdminUser = Depends(require_admin_permission(AdminPermissions.USER_VIEW)),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _: bool = Depends(apply_admin_rate_limit)
):
    """Get user activity history including queries, transactions, and login events."""
    audit_service = AuditService()

    # Log the admin action
    await audit_service.log_action(
        admin_user_id=current_admin.id,
        action_type="user_activity_view",
        resource_type="user",
        resource_id=user_id,
        details={"days": days},
        ip_address=getattr(request.client, "host", None) if request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
        db=db
    )

    admin_service = AdminService()
    activity = await admin_service.get_user_activity(user_id, days, db)

    return activity


@router.get("/users/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: str,
    current_admin: AdminUser = Depends(require_admin_permission(AdminPermissions.USER_VIEW)),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _: bool = Depends(apply_admin_rate_limit)
):
    """Get comprehensive user statistics."""
    audit_service = AuditService()

    # Log the admin action
    await audit_service.log_action(
        admin_user_id=current_admin.id,
        action_type="user_stats_view",
        resource_type="user",
        resource_id=user_id,
        ip_address=getattr(request.client, "host", None) if request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
        db=db
    )

    admin_service = AdminService()
    stats = await admin_service.get_user_stats(user_id, db)

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return stats


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    reason: str,
    current_admin: AdminUser = Depends(require_admin_permission(AdminPermissions.USER_DELETE)),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _: bool = Depends(apply_admin_rate_limit)
):
    """
    Delete a user account (soft delete - marks as deleted but preserves data).
    Requires USER_DELETE permission.
    """
    audit_service = AuditService()
    admin_service = AdminService()

    # Get user before deletion
    user = await admin_service.get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Perform soft delete
    await admin_service.soft_delete_user(
        user_id=user_id,
        reason=reason,
        admin_user_id=current_admin.id,
        db=db
    )

    # Log the admin action
    await audit_service.log_action(
        admin_user_id=current_admin.id,
        action_type="user_delete",
        resource_type="user",
        resource_id=user_id,
        details={
            "user_email": user.email,
            "reason": reason,
            "deletion_type": "soft_delete"
        },
        ip_address=getattr(request.client, "host", None) if request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
        db=db
    )

    # Log security event
    await log_security_event(
        event_type="user_deleted",
        severity="high",
        details={
            "user_id": user_id,
            "user_email": user.email,
            "admin_user_id": current_admin.id,
            "reason": reason
        },
        request=request,
        db=db,
        user_id=user_id,
        admin_user_id=current_admin.id
    )

    return {"message": "User deleted successfully", "user_id": user_id}


@router.post("/users/{user_id}/admin-role")
async def assign_admin_role(
    user_id: str,
    admin_role: str,
    permissions: Optional[list[str]] = None,
    current_admin: AdminUser = Depends(require_admin_permission(AdminPermissions.USER_MANAGE)),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _: bool = Depends(apply_admin_rate_limit)
):
    """Assign admin role to a user."""
    audit_service = AuditService()
    admin_service = AdminService()

    # Validate admin role
    valid_roles = ["super_admin", "admin", "moderator", "viewer"]
    if admin_role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid admin role. Must be one of: {', '.join(valid_roles)}"
        )

    # Only super admins can create other super admins
    if admin_role == "super_admin" and current_admin.admin_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can assign super admin role"
        )

    # Get user
    user = await admin_service.get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Create admin user
    admin_user = await admin_service.create_admin_user(
        user_id=user_id,
        admin_role=admin_role,
        permissions=permissions,
        created_by=current_admin.id,
        db=db
    )

    # Log the admin action
    await audit_service.log_action(
        admin_user_id=current_admin.id,
        action_type="admin_role_assigned",
        resource_type="user",
        resource_id=user_id,
        details={
            "user_email": user.email,
            "admin_role": admin_role,
            "permissions": permissions,
            "admin_user_id": admin_user.id
        },
        ip_address=getattr(request.client, "host", None) if request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
        db=db
    )

    # Log security event
    await log_security_event(
        event_type="admin_role_assigned",
        severity="high",
        details={
            "user_id": user_id,
            "user_email": user.email,
            "admin_role": admin_role,
            "assigned_by": current_admin.id
        },
        request=request,
        db=db,
        user_id=user_id,
        admin_user_id=current_admin.id
    )

    return {"message": "Admin role assigned successfully", "admin_user_id": admin_user.id}


@router.delete("/users/{user_id}/admin-role")
async def revoke_admin_role(
    user_id: str,
    reason: str,
    current_admin: AdminUser = Depends(require_admin_permission(AdminPermissions.USER_MANAGE)),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _: bool = Depends(apply_admin_rate_limit)
):
    """Revoke admin role from a user."""
    audit_service = AuditService()
    admin_service = AdminService()

    # Get admin user
    result = await db.execute(
        select(AdminUser).join(User).where(User.id == user_id)
    )
    admin_user = result.scalar_one_or_none()

    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found"
        )

    # Prevent self-revocation
    if admin_user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke your own admin role"
        )

    # Only super admins can revoke super admin roles
    if admin_user.admin_role == "super_admin" and current_admin.admin_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can revoke super admin roles"
        )

    # Get user for logging
    user = await admin_service.get_user_by_id(user_id, db)

    # Revoke admin role
    await admin_service.revoke_admin_role(user_id, current_admin.id, db)

    # Log the admin action
    await audit_service.log_action(
        admin_user_id=current_admin.id,
        action_type="admin_role_revoked",
        resource_type="user",
        resource_id=user_id,
        details={
            "user_email": user.email if user else None,
            "revoked_role": admin_user.admin_role,
            "reason": reason
        },
        ip_address=getattr(request.client, "host", None) if request.client else None,
        user_agent=request.headers.get("user-agent", "") if request else "",
        db=db
    )

    # Log security event
    await log_security_event(
        event_type="admin_role_revoked",
        severity="high",
        details={
            "user_id": user_id,
            "user_email": user.email if user else None,
            "revoked_role": admin_user.admin_role,
            "revoked_by": current_admin.id,
            "reason": reason
        },
        request=request,
        db=db,
        user_id=user_id,
        admin_user_id=current_admin.id
    )

    return {"message": "Admin role revoked successfully"}
