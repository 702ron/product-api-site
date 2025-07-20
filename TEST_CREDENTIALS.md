# Test Credentials

This file contains test account credentials for easy access during development and testing.

## Test User Account

**Purpose**: Regular user account for testing standard features
- **Email**: `testuser@example.com`
- **Password**: `testpass123`
- **Credits**: 100
- **Role**: Standard User
- **User ID**: `94d44579-a25e-4158-b83d-2eba862a3a97`

### Available Features:
- Product lookup
- FNSKU conversion
- Price monitoring
- Analytics dashboard
- Credit management

---

## Admin Account

**Purpose**: Administrator account with full system access
- **Email**: `admin@example.com`
- **Password**: `adminpass123`
- **Credits**: 1000
- **Role**: Super Admin
- **User ID**: `56740948-6b23-40ca-8539-aaf63c912a6d`
- **Admin Privileges ID**: `805cb3c2-5951-400c-80b3-1689224c60bc`

### Admin Permissions:
- ✅ User Management
- ✅ System Monitoring
- ✅ Security Management
- ✅ Audit Logs
- ✅ Data Export
- ✅ User Credits Management
- ✅ User Status Management
- ✅ System Configuration
- ✅ Admin Management
- ✅ Billing Management
- ✅ Content Moderation
- ✅ API Management

### Admin Dashboard Access:
Navigate to `/admin` after logging in to access the admin dashboard with:
- Overview metrics
- User management (view, activate/deactivate, adjust credits)
- System health monitoring
- Security events
- Data export functionality

---

## Application URLs

- **Frontend**: http://localhost:3001/
- **Backend API**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/docs
- **Admin Dashboard**: http://localhost:3001/admin (login with admin account)

---

## Quick Login Steps

1. Start the backend: `DATABASE_URL="sqlite+aiosqlite:///./test.db" uv run uvicorn app.main:app --reload --port 8000`
2. Start the frontend: `cd frontend && npm run dev`
3. Open browser to http://localhost:3001/
4. Use credentials above to login
5. For admin features, login with admin account and navigate to `/admin`

---

## Security Notes

⚠️ **Important**: These are test credentials for development only. Do not use in production!

- Passwords are hashed using bcrypt
- Admin account has full system privileges
- Regular test user has standard access only
- Both accounts are created in the SQLite test database

---

## Database Information

- **Database**: SQLite (`test.db`)
- **Admin Tables**: Created and populated
- **User Tables**: Standard user schema
- **Migration Status**: All admin dashboard migrations applied

The admin dashboard system is fully functional with role-based access control, audit logging, and comprehensive user management capabilities.