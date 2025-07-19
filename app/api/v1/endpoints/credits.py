"""
Credit management endpoints for balance, transactions, and package purchases.
"""
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user, InsufficientCreditsError
from app.models.models import User
from app.services.credit_service import credit_service
from app.schemas.credits import (
    CreditBalance, CreditTransactionResponse, CreditDeductionRequest,
    CreditDeductionResponse, CreditRefundRequest, CreditRefundResponse,
    CheckoutSessionRequest, CheckoutSessionResponse, CreditPackageInfo,
    TransactionHistoryRequest, TransactionHistoryResponse,
    UsageSummaryRequest, UsageSummaryResponse, BulkOperationRequest,
    BulkOperationResponse, CreditPackage, TransactionType, OperationType
)

router = APIRouter()

# Credit package definitions
CREDIT_PACKAGES = {
    CreditPackage.STARTER: {
        "credits": 100,
        "price_cents": 1000,  # $10.00
        "description": "Perfect for getting started",
        "popular": False
    },
    CreditPackage.PROFESSIONAL: {
        "credits": 500,
        "price_cents": 4500,  # $45.00 (10% discount)
        "description": "Great for regular users",
        "popular": True
    },
    CreditPackage.BUSINESS: {
        "credits": 1000,
        "price_cents": 8000,  # $80.00 (20% discount)
        "description": "Ideal for businesses",
        "popular": False
    },
    CreditPackage.ENTERPRISE: {
        "credits": 5000,
        "price_cents": 35000,  # $350.00 (30% discount)
        "description": "For high-volume usage",
        "popular": False
    }
}


@router.get("/balance", response_model=CreditBalance)
async def get_credit_balance(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's credit balance and summary information.
    """
    # Get usage summary for additional context
    usage_summary = await credit_service.get_usage_summary(db, current_user.id, days=30)
    
    # Check for low balance warning
    low_balance_warning = await credit_service.check_low_credit_warning(
        db, current_user.id, warning_threshold=10
    )
    
    # Get last transaction
    transactions = await credit_service.get_transaction_history(
        db, current_user.id, limit=1
    )
    last_transaction_at = transactions[0].created_at if transactions else None
    
    return CreditBalance(
        user_id=current_user.id,
        current_balance=current_user.credit_balance,
        total_purchased=usage_summary.get('total_credits_purchased', 0),
        total_used=usage_summary.get('total_credits_used', 0),
        last_transaction_at=last_transaction_at,
        low_balance_warning=low_balance_warning
    )


@router.post("/deduct", response_model=CreditDeductionResponse)
async def deduct_credits(
    request: CreditDeductionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Deduct credits for an API operation.
    
    This endpoint is typically called by other services, not directly by users.
    """
    try:
        # Calculate cost if not provided
        cost = request.cost
        if cost is None:
            cost = await credit_service.calculate_operation_cost(request.operation.value)
        
        # Deduct credits
        await credit_service.deduct_credits(
            db=db,
            user_id=current_user.id,
            operation=request.operation.value,
            cost=cost,
            description=request.description,
            extra_data=request.extra_data
        )
        
        # Get updated balance
        updated_balance = await credit_service.get_user_balance(db, current_user.id)
        
        # Get the transaction ID (latest transaction for this user)
        transactions = await credit_service.get_transaction_history(
            db, current_user.id, limit=1
        )
        transaction_id = transactions[0].id if transactions else 0
        
        return CreditDeductionResponse(
            success=True,
            credits_deducted=cost,
            remaining_balance=updated_balance,
            transaction_id=transaction_id,
            operation=request.operation.value
        )
        
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deduct credits: {str(e)}"
        )


@router.post("/refund", response_model=CreditRefundResponse)
async def refund_credits(
    request: CreditRefundRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Refund credits to user account (e.g., for failed operations).
    
    This endpoint is typically called by other services when operations fail.
    """
    try:
        await credit_service.refund_credits(
            db=db,
            user_id=current_user.id,
            amount=request.amount,
            reason=request.reason,
            original_operation=request.original_operation,
            extra_data=request.extra_data
        )
        
        # Get updated balance
        updated_balance = await credit_service.get_user_balance(db, current_user.id)
        
        # Get the transaction ID
        transactions = await credit_service.get_transaction_history(
            db, current_user.id, limit=1
        )
        transaction_id = transactions[0].id if transactions else 0
        
        return CreditRefundResponse(
            success=True,
            credits_refunded=request.amount,
            new_balance=updated_balance,
            transaction_id=transaction_id,
            reason=request.reason
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refund credits: {str(e)}"
        )


@router.get("/history", response_model=TransactionHistoryResponse)
async def get_transaction_history(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    transaction_type: Optional[TransactionType] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    Get user's credit transaction history with filtering and pagination.
    """
    try:
        transactions = await credit_service.get_transaction_history(
            db=db,
            user_id=current_user.id,
            limit=limit + 1,  # Get one extra to check if there are more
            offset=offset,
            transaction_type=transaction_type.value if transaction_type else None,
            start_date=start_date,
            end_date=end_date
        )
        
        # Check if there are more transactions
        has_more = len(transactions) > limit
        if has_more:
            transactions = transactions[:limit]
        
        # Get summary for the current period
        summary = await credit_service.get_usage_summary(db, current_user.id, days=30)
        
        return TransactionHistoryResponse(
            transactions=[CreditTransactionResponse.model_validate(t) for t in transactions],
            total_count=len(transactions),
            has_more=has_more,
            summary=summary
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transaction history: {str(e)}"
        )


@router.get("/usage-summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=30, ge=1, le=365)
):
    """
    Get usage summary for the specified period.
    """
    try:
        summary = await credit_service.get_usage_summary(db, current_user.id, days)
        
        return UsageSummaryResponse(
            period_days=summary['period_days'],
            start_date=datetime.fromisoformat(summary['start_date']),
            end_date=datetime.fromisoformat(summary['end_date']),
            total_credits_used=summary['total_credits_used'],
            total_credits_purchased=summary['total_credits_purchased'],
            net_credit_change=summary['net_credit_change'],
            usage_by_operation=summary['usage_by_operation']
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage summary: {str(e)}"
        )


@router.get("/packages", response_model=List[CreditPackageInfo])
async def get_credit_packages():
    """
    Get available credit packages with pricing information.
    """
    packages = []
    
    for package_type, info in CREDIT_PACKAGES.items():
        # Calculate savings percentage
        base_price_per_credit = CREDIT_PACKAGES[CreditPackage.STARTER]["price_cents"] / CREDIT_PACKAGES[CreditPackage.STARTER]["credits"]
        current_price_per_credit = info["price_cents"] / info["credits"]
        savings_percent = ((base_price_per_credit - current_price_per_credit) / base_price_per_credit) * 100
        
        packages.append(CreditPackageInfo(
            package=package_type,
            credits=info["credits"],
            price_cents=info["price_cents"],
            price_usd=info["price_cents"] / 100,
            savings_percent=max(0, savings_percent) if package_type != CreditPackage.STARTER else None,
            description=info["description"],
            popular=info["popular"]
        ))
    
    return packages


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create Stripe checkout session for credit purchase.
    
    This endpoint will be implemented in Task 5 - Stripe Integration.
    """
    # This is a placeholder - full implementation in Task 5
    if request.package not in CREDIT_PACKAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credit package"
        )
    
    package_info = CREDIT_PACKAGES[request.package]
    
    # For now, return mock response
    return CheckoutSessionResponse(
        checkout_url=f"https://checkout.stripe.com/mock-session-url",
        session_id="mock_session_id",
        package_info=package_info
    )


@router.post("/bulk-operation-cost", response_model=BulkOperationResponse)
async def calculate_bulk_operation_cost(
    request: BulkOperationRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Calculate cost for bulk operations with potential discounts.
    """
    try:
        # Calculate base cost
        base_cost = await credit_service.calculate_operation_cost(
            request.operation.value, count=request.item_count
        )
        
        # Determine if bulk discount was applied
        individual_cost = await credit_service.calculate_operation_cost(request.operation.value)
        bulk_discount_applied = base_cost < (individual_cost * request.item_count)
        
        # Estimate duration (rough estimate)
        estimated_duration = request.item_count * 2  # 2 seconds per item average
        
        return BulkOperationResponse(
            operation=request.operation,
            item_count=request.item_count,
            total_cost=base_cost,
            cost_per_item=base_cost / request.item_count,
            estimated_duration_seconds=estimated_duration,
            bulk_discount_applied=bulk_discount_applied
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate bulk operation cost: {str(e)}"
        )