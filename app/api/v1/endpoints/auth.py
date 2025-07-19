"""
Authentication endpoints for user registration, login, and profile management.
"""
import uuid
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from supabase import Client, create_client

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    get_current_user, get_current_active_user, create_access_token,
    verify_supabase_jwt, create_user_access_token
)
from app.models.models import User
from app.schemas.auth import (
    UserRegister, UserLogin, UserResponse, TokenResponse,
    UserProfile, SupabaseUserCreate
)

router = APIRouter()

# Supabase client
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user with email and password.
    
    Creates user in both Supabase and local database.
    """
    # Check if user already exists in local database
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
    
    try:
        # Create user in Supabase
        supabase_response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "full_name": user_data.full_name
                }
            }
        })
        
        if supabase_response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user in authentication service"
            )
        
        # Create user in local database
        db_user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            supabase_user_id=supabase_response.user.id,
            credit_balance=10,  # 10 free trial credits
            is_active=True
        )
        
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        # Create access token
        access_token = create_user_access_token(db_user)
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserResponse.model_validate(db_user)
        )
        
    except Exception as e:
        await db.rollback()
        if "already registered" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    user_credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user with email and password.
    
    Validates credentials with Supabase and returns JWT token.
    """
    try:
        # Authenticate with Supabase
        supabase_response = supabase.auth.sign_in_with_password({
            "email": user_credentials.email,
            "password": user_credentials.password
        })
        
        if supabase_response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Get user from local database
        result = await db.execute(
            select(User).where(User.supabase_user_id == supabase_response.user.id)
        )
        db_user = result.scalar_one_or_none()
        
        if db_user is None:
            # Create user in local database if not exists
            db_user = User(
                email=user_credentials.email,
                supabase_user_id=supabase_response.user.id,
                credit_balance=10,  # 10 free trial credits
                is_active=True
            )
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)
        
        if not db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        # Create access token
        access_token = create_user_access_token(db_user)
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserResponse.model_validate(db_user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user profile information.
    
    Returns user details including credit balance and usage statistics.
    """
    # Get usage statistics (optional)
    from sqlalchemy import func
    from app.models.models import CreditTransaction, QueryLog
    
    # Get total credits used
    credits_used_result = await db.execute(
        select(func.sum(CreditTransaction.amount))
        .where(
            CreditTransaction.user_id == current_user.id,
            CreditTransaction.transaction_type == 'usage'
        )
    )
    total_credits_used = abs(credits_used_result.scalar() or 0)
    
    # Get total credits purchased
    credits_purchased_result = await db.execute(
        select(func.sum(CreditTransaction.amount))
        .where(
            CreditTransaction.user_id == current_user.id,
            CreditTransaction.transaction_type == 'purchase'
        )
    )
    total_credits_purchased = credits_purchased_result.scalar() or 0
    
    # Get total queries
    queries_result = await db.execute(
        select(func.count(QueryLog.id))
        .where(QueryLog.user_id == current_user.id)
    )
    total_queries = queries_result.scalar() or 0
    
    profile = UserProfile.model_validate(current_user)
    profile.total_queries = total_queries
    profile.total_credits_used = total_credits_used
    profile.total_credits_purchased = total_credits_purchased
    
    return profile


@router.post("/logout")
async def logout_user():
    """
    Logout user (client-side token invalidation).
    
    Since we're using stateless JWT tokens, logout is handled on the client side
    by removing the token. This endpoint serves as a confirmation.
    """
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    current_user: User = Depends(get_current_user)
):
    """
    Refresh user access token.
    
    Generates a new access token for the authenticated user.
    """
    access_token = create_user_access_token(current_user)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer", 
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(current_user)
    )


@router.post("/verify")
async def verify_token(
    current_user: User = Depends(get_current_active_user)
):
    """
    Verify that the provided token is valid.
    
    Returns user information if token is valid.
    """
    return {
        "valid": True,
        "user": UserResponse.model_validate(current_user)
    }


@router.delete("/account")
async def delete_account(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user account (soft delete).
    
    Deactivates the account rather than permanently deleting it.
    """
    current_user.is_active = False
    await db.commit()
    
    return {"message": "Account successfully deactivated"}