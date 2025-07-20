name: "Complete Admin Dashboard System PRP"
description: |
  Comprehensive admin dashboard with user management, system monitoring, API analytics, billing management, content moderation, configuration management, audit logging, real-time notifications, data export, and security monitoring capabilities.

---

## Goal

Build a comprehensive admin dashboard system that provides centralized administrative control over the Amazon Product Intelligence Platform with real-time monitoring, user management, system analytics, billing oversight, content moderation, configuration management, audit logging, notifications, data export capabilities, and security monitoring.

## Why

- **Centralized Control**: Provide administrators with a single interface to manage all aspects of the platform
- **Operational Visibility**: Real-time insights into system health, user activity, and business metrics
- **User Management**: Streamlined user administration including roles, permissions, and account status
- **Revenue Optimization**: Monitor billing, subscriptions, and credit usage patterns for business intelligence
- **Security Compliance**: Comprehensive audit trails and security monitoring for compliance and safety
- **Data-Driven Decisions**: Export capabilities and analytics for strategic planning
- **Proactive Management**: Real-time alerts and notifications for immediate issue response
- **Content Quality**: Moderation tools to ensure product data integrity and user-generated content quality

## What

A full-featured admin dashboard system with the following capabilities:

### Success Criteria

- [ ] User management system with CRUD operations, role assignments, and account status control
- [ ] Real-time system monitoring with health checks, performance metrics, and error tracking
- [ ] Comprehensive API usage analytics with usage patterns, rate limiting data, and endpoint performance
- [ ] Billing and subscription management with payment tracking, plan changes, and credit management
- [ ] Content moderation system for reviewing flagged content and managing product data quality
- [ ] Configuration management interface for system settings and feature flags
- [ ] Complete audit logging system tracking all admin actions with searchable history
- [ ] Real-time notifications and alert system with configurable thresholds
- [ ] Data export capabilities for reports, analytics, and compliance
- [ ] Security monitoring dashboard with failed login tracking and suspicious activity alerts
- [ ] Role-based access control (RBAC) for different admin privilege levels
- [ ] Real-time dashboard with live metrics, charts, and system status indicators

## All Needed Context

### Documentation & References

```yaml
# MUST READ - Include these in your context window
- file: app/models/models.py
  why: Existing data models for users, transactions, queries, webhooks, monitoring

- file: app/core/security.py
  why: Authentication patterns, user permissions, JWT handling

- file: app/services/monitoring_service.py
  why: Existing monitoring infrastructure, metrics collection patterns

- file: app/services/notification_service.py
  why: Notification patterns for alerts and system communications

- file: app/core/config.py
  why: Configuration management patterns and environment variables

- file: frontend/src/App.tsx
  why: Existing frontend routing structure and protected routes pattern

- file: frontend/src/components/Layout.tsx
  why: Current layout structure and navigation patterns

- file: app/api/v1/endpoints/auth.py
  why: Authentication endpoint patterns and user session management

- file: app/core/database.py
  why: Database connection patterns and session management

- file: app/monitoring/metrics.py
  why: Existing metrics collection and monitoring infrastructure
```

### Current Codebase Structure

```bash
product_api_site/
├── app/
│   ├── api/v1/endpoints/          # API endpoints (auth, products, credits, monitoring)
│   ├── core/                      # Core utilities (config, security, database, exceptions)
│   ├── models/                    # SQLAlchemy models (User, transactions, monitoring)
│   ├── services/                  # Business logic (amazon, credit, payment, monitoring, notification)
│   ├── schemas/                   # Pydantic schemas for API validation
│   ├── workers/                   # Background workers and daemons
│   ├── monitoring/                # Metrics collection and monitoring infrastructure
│   └── tests/                     # Test suite
├── frontend/src/
│   ├── components/               # React components (auth, layout, forms)
│   ├── pages/                    # Page components (dashboard, analytics, etc.)
│   ├── contexts/                 # React contexts (auth)
│   ├── lib/                      # API client and utilities
│   └── types/                    # TypeScript type definitions
├── alembic/                      # Database migrations
└── PRPs/                         # Product Requirement Prompts and documentation
```

### Desired Codebase Structure with New Admin Files

```bash
# Backend Admin Components
app/
├── models/
│   └── admin_models.py           # Admin-specific models (AdminUser, AdminSession, AdminAction, SystemConfig)
├── api/v1/endpoints/
│   └── admin/
│       ├── __init__.py
│       ├── users.py              # User management endpoints
│       ├── system.py             # System monitoring endpoints
│       ├── analytics.py          # API analytics endpoints
│       ├── billing.py            # Billing management endpoints
│       ├── content.py            # Content moderation endpoints
│       ├── config.py             # Configuration management endpoints
│       ├── audit.py              # Audit log endpoints
│       ├── notifications.py     # Notification management endpoints
│       ├── exports.py            # Data export endpoints
│       └── security.py          # Security monitoring endpoints
├── services/
│   ├── admin_service.py          # Core admin business logic
│   ├── audit_service.py          # Audit logging service
│   ├── export_service.py         # Data export service
│   └── security_monitoring_service.py  # Security monitoring service
├── schemas/
│   └── admin.py                  # Admin-specific Pydantic schemas
└── middleware/
    └── admin_auth.py             # Admin authentication middleware

# Frontend Admin Components
frontend/src/
├── pages/
│   └── admin/
│       ├── AdminDashboard.tsx    # Main admin dashboard
│       ├── UserManagement.tsx    # User CRUD and management
│       ├── SystemMonitoring.tsx  # System health and performance
│       ├── ApiAnalytics.tsx      # API usage analytics
│       ├── BillingManagement.tsx # Billing and subscription management
│       ├── ContentModeration.tsx # Content review and moderation
│       ├── ConfigManagement.tsx  # System configuration interface
│       ├── AuditLogs.tsx         # Audit log viewer
│       ├── NotificationCenter.tsx # Notification management
│       ├── DataExports.tsx       # Export management interface
│       └── SecurityMonitoring.tsx # Security dashboard
├── components/
│   └── admin/
│       ├── AdminLayout.tsx       # Admin-specific layout
│       ├── AdminNavigation.tsx   # Admin navigation menu
│       ├── AdminHeader.tsx       # Admin header with user info
│       ├── UserTable.tsx         # User management table
│       ├── MetricsChart.tsx      # Real-time metrics charts
│       ├── AlertsPanel.tsx       # Alerts and notifications panel
│       ├── AuditLogTable.tsx     # Audit log display table
│       ├── ConfigEditor.tsx      # Configuration editing interface
│       ├── ExportBuilder.tsx     # Data export query builder
│       └── SecurityAlerts.tsx    # Security monitoring alerts
├── contexts/
│   └── AdminContext.tsx          # Admin-specific context and state
└── types/
    └── admin.ts                  # Admin-specific TypeScript types
```

### Known Gotchas & Library Quirks

```python
# CRITICAL: FastAPI requires async functions for all endpoints
# CRITICAL: SQLAlchemy relationships must use back_populates correctly
# CRITICAL: Pydantic v2 syntax - use Field() for validation
# CRITICAL: PostgreSQL UUID fields must use String(36) not UUID type in current setup
# CRITICAL: React Query (TanStack) requires proper invalidation for real-time updates
# CRITICAL: JWT tokens include both 'sub' and 'user_id' for compatibility
# CRITICAL: Redis connection pooling required for high-frequency monitoring
# CRITICAL: Stripe webhooks require idempotency handling via webhook_logs table
# CRITICAL: All database operations should use async sessions
# CRITICAL: Metrics collection uses Prometheus format - counter.inc(), histogram.observe()
# CRITICAL: Admin actions MUST be logged for audit compliance
# CRITICAL: Real-time updates require WebSocket or SSE implementation
# CRITICAL: Rate limiting must be bypassed for admin endpoints with proper auth
# CRITICAL: Export operations should be background jobs for large datasets
```

## Implementation Blueprint

### Data Models and Structure

Create comprehensive admin data models ensuring audit trails and security:

```python
# Admin-specific models extending existing user system
class AdminUser(Base):
    """Admin user with elevated permissions"""
    __tablename__ = "admin_users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)  # Link to regular user
    admin_role = Column(Enum("super_admin", "admin", "moderator", "viewer"))
    permissions = Column(JSON)  # Granular permissions
    created_by = Column(String(36), ForeignKey("admin_users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AdminSession(Base):
    """Track admin login sessions for security"""
    __tablename__ = "admin_sessions"
    
    id = Column(String(36), primary_key=True)
    admin_user_id = Column(String(36), ForeignKey("admin_users.id"))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    login_at = Column(DateTime, default=datetime.utcnow)
    logout_at = Column(DateTime)
    is_active = Column(Boolean, default=True)

class AdminAction(Base):
    """Comprehensive audit log for all admin actions"""
    __tablename__ = "admin_actions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    admin_user_id = Column(String(36), ForeignKey("admin_users.id"))
    action_type = Column(String(100))  # 'user_create', 'user_delete', 'config_update', etc.
    resource_type = Column(String(100))  # 'user', 'config', 'system', etc.
    resource_id = Column(String(255))
    details = Column(JSON)  # Action-specific details
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class SystemConfig(Base):
    """Dynamic system configuration management"""
    __tablename__ = "system_config"
    
    key = Column(String(255), primary_key=True)
    value = Column(JSON)
    description = Column(Text)
    config_type = Column(String(50))  # 'feature_flag', 'setting', 'threshold', etc.
    is_sensitive = Column(Boolean, default=False)  # Hide value in UI if true
    updated_by = Column(String(36), ForeignKey("admin_users.id"))
    updated_at = Column(DateTime, default=datetime.utcnow)

class SecurityEvent(Base):
    """Security monitoring events"""
    __tablename__ = "security_events"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_type = Column(String(100))  # 'failed_login', 'suspicious_activity', 'rate_limit_exceeded'
    severity = Column(String(20))  # 'low', 'medium', 'high', 'critical'
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    details = Column(JSON)
    resolved = Column(Boolean, default=False)
    resolved_by = Column(String(36), ForeignKey("admin_users.id"))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
```

### List of Tasks to Complete

```yaml
Task 1: Create Admin Database Models and Migrations
MODIFY app/models/models.py:
  - ADD admin-specific models (AdminUser, AdminSession, AdminAction, SystemConfig, SecurityEvent)
  - PRESERVE existing model patterns and relationships
  - ENSURE proper foreign key relationships

CREATE alembic migration:
  - ADD new admin tables
  - PRESERVE existing data
  - ADD necessary indexes for performance

Task 2: Implement Admin Authentication and Authorization
CREATE app/middleware/admin_auth.py:
  - IMPLEMENT admin role-based authentication
  - MIRROR pattern from app/core/security.py
  - ADD permission checking decorators

MODIFY app/api/deps.py:
  - ADD admin authentication dependencies
  - IMPLEMENT role-based access control functions

Task 3: Create Admin API Endpoints
CREATE app/api/v1/endpoints/admin/ directory with modules:
  - users.py (user management CRUD)
  - system.py (system monitoring and health)
  - analytics.py (API usage analytics)
  - billing.py (billing and subscription management)
  - content.py (content moderation)
  - config.py (configuration management)
  - audit.py (audit log access)
  - notifications.py (notification management)
  - exports.py (data export functionality)
  - security.py (security monitoring)

Task 4: Implement Admin Services
CREATE app/services/admin_service.py:
  - IMPLEMENT core admin business logic
  - PATTERN: Use existing service patterns from app/services/

CREATE app/services/audit_service.py:
  - IMPLEMENT comprehensive audit logging
  - ENSURE all admin actions are logged

CREATE app/services/export_service.py:
  - IMPLEMENT data export functionality
  - USE background jobs for large exports

CREATE app/services/security_monitoring_service.py:
  - IMPLEMENT security event detection and monitoring
  - INTEGRATE with existing monitoring infrastructure

Task 5: Create Admin Pydantic Schemas
CREATE app/schemas/admin.py:
  - DEFINE all admin-related request/response schemas
  - MIRROR patterns from existing schemas
  - ENSURE proper validation and serialization

Task 6: Create Admin Frontend Components
CREATE frontend/src/contexts/AdminContext.tsx:
  - IMPLEMENT admin state management
  - PATTERN: Follow existing AuthContext pattern

CREATE frontend/src/components/admin/ components:
  - AdminLayout.tsx (admin-specific layout)
  - AdminNavigation.tsx (navigation menu)
  - UserTable.tsx (user management interface)
  - MetricsChart.tsx (real-time charts)
  - AlertsPanel.tsx (alerts and notifications)
  - AuditLogTable.tsx (audit log display)
  - ConfigEditor.tsx (configuration interface)

Task 7: Create Admin Pages
CREATE frontend/src/pages/admin/ pages:
  - AdminDashboard.tsx (main dashboard)
  - UserManagement.tsx (user CRUD)
  - SystemMonitoring.tsx (system health)
  - ApiAnalytics.tsx (API analytics)
  - BillingManagement.tsx (billing interface)
  - ContentModeration.tsx (content review)
  - ConfigManagement.tsx (system config)
  - AuditLogs.tsx (audit viewer)
  - SecurityMonitoring.tsx (security dashboard)

Task 8: Implement Real-time Features
MODIFY existing monitoring infrastructure:
  - ADD WebSocket support for real-time updates
  - IMPLEMENT real-time metrics streaming
  - ADD live notification system

Task 9: Add Admin Routes and Navigation
MODIFY frontend/src/App.tsx:
  - ADD admin routes with proper protection
  - IMPLEMENT admin role checking

Task 10: Testing and Validation
CREATE comprehensive test suite:
  - Unit tests for all admin services
  - Integration tests for admin endpoints
  - Frontend component tests
  - Security and permission tests
```

### Per Task Pseudocode

```python
# Task 3: Admin API Endpoints Pattern
# app/api/v1/endpoints/admin/users.py
@router.get("/users", response_model=List[AdminUserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    role_filter: Optional[str] = None,
    current_admin: AdminUser = Depends(require_admin_permission("user_management")),
    db: AsyncSession = Depends(get_db)
):
    # PATTERN: Use existing pagination patterns
    # PATTERN: Implement search and filtering
    # CRITICAL: Log all admin actions via audit_service
    await audit_service.log_action(
        admin_user_id=current_admin.id,
        action_type="user_list_view",
        resource_type="user",
        details={"search": search, "role_filter": role_filter}
    )
    
    return await admin_service.get_users_paginated(skip, limit, search, role_filter, db)

# Task 4: Admin Service Pattern
# app/services/admin_service.py
async def update_user_status(
    user_id: str,
    is_active: bool,
    admin_user_id: str,
    db: AsyncSession
) -> User:
    # PATTERN: Always validate permissions first
    # PATTERN: Use existing error handling patterns
    # CRITICAL: Log all user modifications
    
    user = await get_user_by_id(user_id, db)
    if not user:
        raise ResourceNotFoundError("User not found", "user", user_id)
    
    old_status = user.is_active
    user.is_active = is_active
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # CRITICAL: Audit log with before/after values
    await audit_service.log_action(
        admin_user_id=admin_user_id,
        action_type="user_status_update",
        resource_type="user",
        resource_id=user_id,
        details={
            "old_status": old_status,
            "new_status": is_active,
            "user_email": user.email
        }
    )
    
    return user

# Task 6: Frontend Component Pattern
// frontend/src/components/admin/UserTable.tsx
const UserTable: React.FC<UserTableProps> = ({ users, onUserUpdate }) => {
  // PATTERN: Use existing table patterns from current components
  // PATTERN: Implement real-time updates via React Query
  // CRITICAL: Show proper loading and error states
  
  const { mutate: updateUserStatus } = useMutation({
    mutationFn: (data: UpdateUserStatusRequest) => 
      adminApi.updateUserStatus(data.userId, data.isActive),
    onSuccess: () => {
      queryClient.invalidateQueries(['admin', 'users']);
      toast.success('User status updated successfully');
    },
    onError: (error) => {
      toast.error('Failed to update user status');
    }
  });

  return (
    <div className="admin-user-table">
      {/* PATTERN: Follow existing table component structure */}
      {/* CRITICAL: Include audit trail information */}
      {/* CRITICAL: Show role-based action permissions */}
    </div>
  );
};
```

### Integration Points

```yaml
DATABASE:
  - migration: "Add admin_users, admin_sessions, admin_actions, system_config, security_events tables"
  - indexes: "CREATE INDEX idx_admin_actions_created_at ON admin_actions(created_at)"
  - indexes: "CREATE INDEX idx_security_events_created_at ON security_events(created_at)"

CONFIG:
  - add to: app/core/config.py
  - pattern: "ADMIN_SESSION_TIMEOUT = int(os.getenv('ADMIN_SESSION_TIMEOUT', '3600'))"
  - pattern: "ADMIN_AUDIT_RETENTION_DAYS = int(os.getenv('ADMIN_AUDIT_RETENTION_DAYS', '365'))"

ROUTES:
  - add to: app/main.py
  - pattern: "app.include_router(admin_router, prefix='/api/v1/admin', tags=['admin'])"

MIDDLEWARE:
  - add to: app/main.py
  - pattern: "app.add_middleware(AdminAuditMiddleware)"

WEBSOCKETS:
  - add to: app/main.py
  - pattern: WebSocket endpoint for real-time admin updates

PERMISSIONS:
  - integrate with: app/core/security.py
  - pattern: Role-based access control decorators
```

## Validation Loop

### Level 1: Syntax & Style

```bash
# Run these FIRST - fix any errors before proceeding
ruff check app/models/admin_models.py app/services/admin_service.py app/api/v1/endpoints/admin/ --fix
mypy app/models/admin_models.py app/services/admin_service.py app/api/v1/endpoints/admin/

# Frontend
cd frontend && npm run type-check
cd frontend && npm run lint

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests

```python
# CREATE test_admin_service.py with comprehensive test cases:
def test_admin_user_creation():
    """Test admin user creation with proper permissions"""
    admin_user = create_admin_user(user_id="test-user", role="admin")
    assert admin_user.admin_role == "admin"
    assert admin_user.is_active is True

def test_audit_logging():
    """Test that all admin actions are properly logged"""
    with mock.patch('app.services.audit_service.log_action') as mock_log:
        await admin_service.update_user_status("user-id", False, "admin-id", db)
        mock_log.assert_called_once()

def test_permission_checking():
    """Test role-based permission enforcement"""
    with pytest.raises(AuthorizationError):
        await admin_service.delete_user("user-id", moderator_user, db)

def test_security_event_detection():
    """Test security monitoring and event creation"""
    event = await security_monitoring_service.create_security_event(
        event_type="failed_login",
        severity="medium",
        ip_address="192.168.1.1"
    )
    assert event.event_type == "failed_login"

def test_data_export_functionality():
    """Test data export with proper formatting"""
    export_data = await export_service.export_user_data(
        format="csv",
        date_range={"start": "2024-01-01", "end": "2024-12-31"}
    )
    assert len(export_data) > 0
    assert "email" in export_data[0].keys()
```

```bash
# Run and iterate until passing:
uv run pytest app/tests/test_admin_service.py app/tests/test_audit_service.py -v
# Frontend tests:
cd frontend && npm test
```

### Level 3: Integration Tests

```bash
# Start the service with admin features
uv run uvicorn app.main:app --reload

# Test admin authentication
curl -X POST http://localhost:8000/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin_password"}'

# Test user management endpoint
curl -X GET http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Test system monitoring endpoint
curl -X GET http://localhost:8000/api/v1/admin/system/health \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Test audit log endpoint
curl -X GET http://localhost:8000/api/v1/admin/audit/logs \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Expected: Proper JSON responses with admin data
# If error: Check logs for authentication and permission issues
```

### Level 4: End-to-End Admin Workflow Testing

```bash
# Test complete admin workflows:

# 1. Admin login and dashboard access
# 2. User management operations (create, update, disable)
# 3. System monitoring and alerts
# 4. Configuration changes
# 5. Data export operations
# 6. Security monitoring and incident response
# 7. Audit log review and search
# 8. Real-time notification handling

# Performance testing for admin dashboard
# Load testing with multiple concurrent admin users
# Security testing for privilege escalation
# Audit compliance validation
```

## Final Validation Checklist

- [ ] All admin endpoints require proper authentication and authorization
- [ ] All admin actions are logged in audit trail with complete details
- [ ] User management CRUD operations work correctly with proper validation
- [ ] System monitoring displays real-time metrics and health status
- [ ] API analytics show accurate usage patterns and performance data
- [ ] Billing management integrates properly with Stripe and credit system
- [ ] Content moderation tools function for reviewing flagged content
- [ ] Configuration management allows safe system setting updates
- [ ] Data export functionality works for all major data types
- [ ] Security monitoring detects and alerts on suspicious activities
- [ ] Real-time notifications work for critical system events
- [ ] Role-based access control properly restricts admin functions
- [ ] Frontend admin interface is responsive and user-friendly
- [ ] All tests pass: `uv run pytest app/tests/ -v`
- [ ] No linting errors: `uv run ruff check app/`
- [ ] No type errors: `uv run mypy app/`
- [ ] Frontend builds without errors: `cd frontend && npm run build`
- [ ] Admin dashboard loads and displays data correctly
- [ ] Security scanning shows no vulnerabilities in admin components

---

## Anti-Patterns to Avoid

- ❌ Don't create admin functionality without proper audit logging
- ❌ Don't skip permission checks for any admin operations
- ❌ Don't expose sensitive configuration values in API responses
- ❌ Don't implement admin features without rate limiting protection
- ❌ Don't create admin endpoints without proper input validation
- ❌ Don't allow admin actions without confirming user identity
- ❌ Don't implement real-time features without proper error handling
- ❌ Don't create data exports without size and time limits
- ❌ Don't skip security monitoring for admin account activities
- ❌ Don't implement configuration changes without backup/rollback capability