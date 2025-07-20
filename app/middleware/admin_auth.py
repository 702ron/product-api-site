"""
Admin authentication and authorization middleware.
"""
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import JWTError, verify_token
from app.models.models import AdminSession, AdminUser, SecurityEvent, User

security = HTTPBearer()


class AdminPermissions:
    """Admin permission constants."""

    # User Management
    USER_VIEW = "user_view"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_MANAGE = "user_manage"

    # System Management
    SYSTEM_VIEW = "system_view"
    SYSTEM_MONITOR = "system_monitor"
    SYSTEM_CONFIG = "system_config"

    # Analytics & Reports
    ANALYTICS_VIEW = "analytics_view"
    ANALYTICS_EXPORT = "analytics_export"

    # Billing Management
    BILLING_VIEW = "billing_view"
    BILLING_MANAGE = "billing_manage"

    # Content Moderation
    CONTENT_VIEW = "content_view"
    CONTENT_MODERATE = "content_moderate"

    # Audit & Security
    AUDIT_VIEW = "audit_view"
    SECURITY_VIEW = "security_view"
    SECURITY_MANAGE = "security_manage"

    # Super Admin
    SUPER_ADMIN = "super_admin"


class AdminRoles:
    """Admin role definitions with permissions."""

    ROLE_PERMISSIONS = {
        "super_admin": [
            AdminPermissions.SUPER_ADMIN,
            # All permissions
            AdminPermissions.USER_VIEW, AdminPermissions.USER_CREATE,
            AdminPermissions.USER_UPDATE, AdminPermissions.USER_DELETE, AdminPermissions.USER_MANAGE,
            AdminPermissions.SYSTEM_VIEW, AdminPermissions.SYSTEM_MONITOR, AdminPermissions.SYSTEM_CONFIG,
            AdminPermissions.ANALYTICS_VIEW, AdminPermissions.ANALYTICS_EXPORT,
            AdminPermissions.BILLING_VIEW, AdminPermissions.BILLING_MANAGE,
            AdminPermissions.CONTENT_VIEW, AdminPermissions.CONTENT_MODERATE,
            AdminPermissions.AUDIT_VIEW, AdminPermissions.SECURITY_VIEW, AdminPermissions.SECURITY_MANAGE,
        ],
        "admin": [
            AdminPermissions.USER_VIEW, AdminPermissions.USER_CREATE,
            AdminPermissions.USER_UPDATE, AdminPermissions.USER_MANAGE,
            AdminPermissions.SYSTEM_VIEW, AdminPermissions.SYSTEM_MONITOR,
            AdminPermissions.ANALYTICS_VIEW, AdminPermissions.ANALYTICS_EXPORT,
            AdminPermissions.BILLING_VIEW, AdminPermissions.BILLING_MANAGE,
            AdminPermissions.CONTENT_VIEW, AdminPermissions.CONTENT_MODERATE,
            AdminPermissions.AUDIT_VIEW, AdminPermissions.SECURITY_VIEW,
        ],
        "moderator": [
            AdminPermissions.USER_VIEW,
            AdminPermissions.SYSTEM_VIEW,
            AdminPermissions.ANALYTICS_VIEW,
            AdminPermissions.BILLING_VIEW,
            AdminPermissions.CONTENT_VIEW, AdminPermissions.CONTENT_MODERATE,
            AdminPermissions.AUDIT_VIEW,
        ],
        "viewer": [
            AdminPermissions.USER_VIEW,
            AdminPermissions.SYSTEM_VIEW,
            AdminPermissions.ANALYTICS_VIEW,
            AdminPermissions.BILLING_VIEW,
            AdminPermissions.CONTENT_VIEW,
            AdminPermissions.AUDIT_VIEW,
        ],
    }


async def get_admin_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> AdminUser:
    """
    Get admin user from JWT token.

    Args:
        credentials: HTTP authorization credentials
        db: Database session

    Returns:
        AdminUser object

    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = credentials.credentials
        payload = verify_token(token)

        # Extract user ID
        user_id: str = payload.get("sub") or payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Find admin user by regular user ID
        result = await db.execute(
            select(AdminUser)
            .join(User)
            .where(
                and_(
                    User.id == user_id,
                    AdminUser.is_active == True,
                    User.is_active == True
                )
            )
        )
        admin_user = result.scalar_one_or_none()

        if admin_user is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        return admin_user

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_admin_session(
    admin_user: AdminUser,
    request: Request,
    db: AsyncSession
) -> bool:
    """
    Verify admin session is valid and update last activity.
    Creates a new session if none exists.

    Args:
        admin_user: Admin user object
        request: FastAPI request object
        db: Database session

    Returns:
        True if session is valid

    Raises:
        HTTPException: If session creation fails
    """
    # Get most recent active session for this admin user
    result = await db.execute(
        select(AdminSession).where(
            and_(
                AdminSession.admin_user_id == admin_user.id,
                AdminSession.is_active == True,
                AdminSession.expires_at > datetime.utcnow()
            )
        ).order_by(AdminSession.login_at.desc()).limit(1)
    )
    session = result.scalar_one_or_none()

    if session is None:
        # Create a new admin session if none exists
        try:
            session = await create_admin_session(admin_user, request, db)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create admin session: {str(e)}"
            )

    # Update last activity
    session.last_activity_at = datetime.utcnow()
    await db.commit()

    return True


def get_admin_permissions(admin_user: AdminUser) -> list[str]:
    """
    Get list of permissions for admin user.

    Args:
        admin_user: Admin user object

    Returns:
        List of permission strings
    """
    # Start with role-based permissions
    role_permissions = AdminRoles.ROLE_PERMISSIONS.get(admin_user.admin_role, [])

    # Add custom permissions if any
    custom_permissions = admin_user.permissions or {}
    
    # Handle both dict and list formats for backward compatibility
    if isinstance(custom_permissions, dict):
        additional_permissions = custom_permissions.get("additional", [])
        removed_permissions = custom_permissions.get("removed", [])
    elif isinstance(custom_permissions, list):
        # Legacy format: just a list of additional permissions
        additional_permissions = custom_permissions
        removed_permissions = []
    else:
        additional_permissions = []
        removed_permissions = []

    # Combine permissions
    all_permissions = set(role_permissions + additional_permissions)
    all_permissions -= set(removed_permissions)

    return list(all_permissions)


def require_admin_permission(permission: str):
    """
    Decorator to require specific admin permission.

    Args:
        permission: Required permission string

    Returns:
        Dependency function for FastAPI
    """
    async def permission_dependency(
        admin_user: AdminUser = Depends(get_admin_user_from_token),
        request: Request = None,
        db: AsyncSession = Depends(get_db)
    ) -> AdminUser:
        # Verify session
        await verify_admin_session(admin_user, request, db)

        # Check permissions
        user_permissions = get_admin_permissions(admin_user)

        # Super admin has all permissions
        if AdminPermissions.SUPER_ADMIN in user_permissions:
            return admin_user

        # Check specific permission
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )

        return admin_user

    return permission_dependency


def require_admin_role(role: str):
    """
    Decorator to require specific admin role.

    Args:
        role: Required admin role

    Returns:
        Dependency function for FastAPI
    """
    async def role_dependency(
        admin_user: AdminUser = Depends(get_admin_user_from_token),
        request: Request = None,
        db: AsyncSession = Depends(get_db)
    ) -> AdminUser:
        # Verify session
        await verify_admin_session(admin_user, request, db)

        # Check role
        if admin_user.admin_role != role and admin_user.admin_role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Admin role '{role}' required"
            )

        return admin_user

    return role_dependency


async def log_security_event(
    event_type: str,
    severity: str,
    details: dict[str, Any],
    request: Request,
    db: AsyncSession,
    user_id: Optional[str] = None,
    admin_user_id: Optional[str] = None
) -> SecurityEvent:
    """
    Log a security event.

    Args:
        event_type: Type of security event
        severity: Event severity level
        details: Event details
        request: FastAPI request object
        db: Database session
        user_id: Optional user ID
        admin_user_id: Optional admin user ID

    Returns:
        Created SecurityEvent object
    """
    # Extract client information
    client_host = getattr(request.client, "host", None) if request.client else None
    user_agent = request.headers.get("user-agent", "")

    # Create security event
    security_event = SecurityEvent(
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        admin_user_id=admin_user_id,
        ip_address=client_host,
        user_agent=user_agent,
        details=details,
        source="admin_panel"
    )

    db.add(security_event)
    await db.commit()
    await db.refresh(security_event)

    return security_event


async def create_admin_session(
    admin_user: AdminUser,
    request: Request,
    db: AsyncSession
) -> AdminSession:
    """
    Create a new admin session.

    Args:
        admin_user: Admin user object
        request: FastAPI request object
        db: Database session

    Returns:
        Created AdminSession object
    """
    # Extract client information
    client_host = getattr(request.client, "host", None) if request.client else None
    user_agent = request.headers.get("user-agent", "")

    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(seconds=settings.admin_session_timeout)

    # Create session
    session = AdminSession(
        admin_user_id=admin_user.id,
        ip_address=client_host,
        user_agent=user_agent,
        expires_at=expires_at
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return session


async def invalidate_admin_sessions(
    admin_user_id: str,
    db: AsyncSession,
    except_session_id: Optional[str] = None
) -> int:
    """
    Invalidate all admin sessions for a user.

    Args:
        admin_user_id: Admin user ID
        db: Database session
        except_session_id: Optional session ID to exclude from invalidation

    Returns:
        Number of invalidated sessions
    """
    # Build query conditions
    conditions = [
        AdminSession.admin_user_id == admin_user_id,
        AdminSession.is_active == True
    ]

    if except_session_id:
        conditions.append(AdminSession.id != except_session_id)

    # Get sessions to invalidate
    result = await db.execute(
        select(AdminSession).where(and_(*conditions))
    )
    sessions = result.scalars().all()

    # Mark sessions as inactive
    for session in sessions:
        session.is_active = False
        session.logout_at = datetime.utcnow()

    await db.commit()

    return len(sessions)
