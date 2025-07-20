"""
User profile and statistics endpoints.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.models import User, CreditTransaction, QueryLog
from app.schemas.auth import UserResponse

router = APIRouter()


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
    profile_update: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Update current user profile.
    """
    # Update allowed fields
    allowed_fields = ['full_name']
    for field in allowed_fields:
        if field in profile_update:
            setattr(current_user, field, profile_update[field])
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse.model_validate(current_user)


@router.get("/me/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current user statistics.
    """
    # Get transaction count
    transaction_count_result = await db.execute(
        select(func.count(CreditTransaction.id)).where(
            CreditTransaction.user_id == current_user.id
        )
    )
    transaction_count = transaction_count_result.scalar() or 0
    
    # Get query count
    query_count_result = await db.execute(
        select(func.count(QueryLog.id)).where(
            QueryLog.user_id == current_user.id
        )
    )
    query_count = query_count_result.scalar() or 0
    
    # Get total spent (sum of deducted credits)
    total_spent_result = await db.execute(
        select(func.sum(CreditTransaction.amount)).where(
            and_(
                CreditTransaction.user_id == current_user.id,
                CreditTransaction.transaction_type == "usage"
            )
        )
    )
    total_spent = abs(total_spent_result.scalar() or 0)
    
    return {
        "user_id": current_user.id,
        "credit_balance": current_user.credits,
        "total_transactions": transaction_count,
        "total_queries": query_count,
        "total_spent": total_spent,
        "is_active": current_user.is_active,
        "member_since": current_user.created_at.isoformat(),
        # Dashboard-specific stats that the frontend expects
        "total_credits": current_user.credits,
        "credits_used_today": 0,  # TODO: Calculate today's usage
        "queries_today": 0,  # TODO: Calculate today's queries  
        "total_conversions": 0,  # TODO: Calculate total conversions
        "conversions_today": 0  # TODO: Calculate today's conversions
    }