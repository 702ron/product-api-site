#!/usr/bin/env python3
"""
Database seeding script for creating initial admin users and test data.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app.core.database import AsyncSessionLocal
from app.models.models import User, AdminUser
from app.core.security import hash_password
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime


async def create_admin_user():
    """Create the admin user and admin privileges record."""
    
    # Get database session
    async with AsyncSessionLocal() as db:
        try:
            # Check if admin user already exists
            result = await db.execute(
                select(User).where(User.email == "admin@example.com")
            )
            admin_user = result.scalar_one_or_none()
            
            if not admin_user:
                print("Creating admin user...")
                # Create the admin user record
                admin_user = User(
                    id="56740948-6b23-40ca-8539-aaf63c912a6d",
                    email="admin@example.com",
                    full_name="System Administrator",
                    hashed_password=hash_password("adminpass123"),
                    credit_balance=1000,
                    is_active=True,
                    is_verified=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(admin_user)
                await db.commit()
                await db.refresh(admin_user)
                print(f"✅ Created admin user: {admin_user.email}")
            else:
                print(f"✅ Admin user already exists: {admin_user.email}")
            
            # Check if AdminUser record exists
            result = await db.execute(
                select(AdminUser).where(AdminUser.user_id == admin_user.id)
            )
            admin_privileges = result.scalar_one_or_none()
            
            if not admin_privileges:
                print("Creating admin privileges...")
                # Create the AdminUser record for elevated permissions
                admin_privileges = AdminUser(
                    id="805cb3c2-5951-400c-80b3-1689224c60bc",
                    user_id=admin_user.id,
                    admin_role="super_admin",
                    permissions=None,  # Super admin gets all permissions by default
                    created_by=None,  # Self-created
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(admin_privileges)
                await db.commit()
                await db.refresh(admin_privileges)
                print(f"✅ Created admin privileges: {admin_privileges.admin_role}")
            else:
                print(f"✅ Admin privileges already exist: {admin_privileges.admin_role}")
            
            # Check if test user exists
            result = await db.execute(
                select(User).where(User.email == "testuser@example.com")
            )
            test_user = result.scalar_one_or_none()
            
            if not test_user:
                print("Creating test user...")
                test_user = User(
                    id="94d44579-a25e-4158-b83d-2eba862a3a97",
                    email="testuser@example.com",
                    full_name="Test User",
                    hashed_password=hash_password("testpass123"),
                    credit_balance=100,
                    is_active=True,
                    is_verified=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(test_user)
                await db.commit()
                await db.refresh(test_user)
                print(f"✅ Created test user: {test_user.email}")
            else:
                print(f"✅ Test user already exists: {test_user.email}")
            
            print("\n🎉 Database seeding completed successfully!")
            print("\nTest Credentials:")
            print("  Admin: admin@example.com / adminpass123")
            print("  User:  testuser@example.com / testpass123")
            
        except Exception as e:
            print(f"❌ Error seeding database: {e}")
            await db.rollback()
            raise


async def main():
    """Main entry point."""
    print("🌱 Seeding database with admin and test users...")
    await create_admin_user()


if __name__ == "__main__":
    asyncio.run(main())