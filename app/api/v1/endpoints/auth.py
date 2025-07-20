"""
Authentication endpoints for user registration, login, and profile management.
"""
import uuid
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.hash import bcrypt

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    get_current_user, get_current_active_user, create_access_token,
    create_user_access_token, verify_password
)
from app.models.models import User
from app.schemas.auth import (
    UserRegister, UserLogin, UserResponse, TokenResponse,
    UserProfile
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register_user(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Register a new user with email and password.
    """
    try:
        # Check if user already exists
        stmt = select(User).where(User.email == user_data.email.lower())
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Hash the password
        hashed_password = bcrypt.hash(user_data.password)
        
        # Create new user
        new_user = User(
            id=str(uuid.uuid4()),
            email=user_data.email.lower(),
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            credit_balance=10,  # Free trial credits
            is_active=True,
            is_verified=True  # Auto-verify for now
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Create access token
        access_token = create_user_access_token(new_user)
        refresh_token = create_user_access_token(new_user, expires_delta=timedelta(days=30))
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,  # Convert to seconds
            user=UserResponse.model_validate(new_user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Login user with email and password.
    """
    try:
        # Find user by email
        stmt = select(User).where(User.email == credentials.email.lower())
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not user.hashed_password or not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )
        
        # Create access token
        access_token = create_user_access_token(user)
        refresh_token = create_user_access_token(user, expires_delta=timedelta(days=30))
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,  # Convert to seconds
            user=UserResponse.model_validate(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current user profile.
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    profile_data: UserProfile,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Update current user profile.
    """
    try:
        # Update user fields
        if profile_data.full_name is not None:
            current_user.full_name = profile_data.full_name
        
        await db.commit()
        await db.refresh(current_user)
        
        return UserResponse.model_validate(current_user)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile update failed: {str(e)}"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Refresh access token.
    """
    try:
        # Create new access token
        access_token = create_user_access_token(current_user)
        refresh_token = create_user_access_token(current_user, expires_delta=timedelta(days=30))
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,  # Convert to seconds
            user=UserResponse.model_validate(current_user)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.post("/logout")
async def logout_user():
    """
    Logout user (client should remove token).
    """
    return {"message": "Successfully logged out"}