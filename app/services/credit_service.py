"""
Credit management service for atomic credit operations and balance tracking.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from app.models.models import User, CreditTransaction
from app.core.security import InsufficientCreditsError

logger = logging.getLogger(__name__)


class CreditService:
    """Service for managing user credits and transactions."""
    
    async def get_user_balance(
        self, 
        db: AsyncSession, 
        user_id: str
    ) -> int:
        """
        Get current credit balance for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Current credit balance
        """
        result = await db.execute(
            select(User.credit_balance).where(User.id == user_id)
        )
        balance = result.scalar_one_or_none()
        return balance or 0
    
    async def deduct_credits(
        self,
        db: AsyncSession,
        user_id: str,
        operation: str,
        cost: int,
        description: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Atomically deduct credits for an API operation.
        
        Args:
            db: Database session
            user_id: User ID
            operation: Operation type (e.g., 'asin_query', 'fnsku_conversion')
            cost: Credits to deduct
            description: Operation description
            extra_data: Additional metadata
            
        Returns:
            True if successful
            
        Raises:
            InsufficientCreditsError: If user lacks sufficient credits
        """
        async with db.begin():
            # Lock user row for update to prevent race conditions
            result = await db.execute(
                select(User).where(User.id == user_id).with_for_update()
            )
            user = result.scalar_one_or_none()
            
            if user is None:
                raise ValueError(f"User {user_id} not found")
            
            # Validate sufficient credits BEFORE deduction
            if user.credit_balance < cost:
                raise InsufficientCreditsError(
                    f"Operation requires {cost} credits, but user has {user.credit_balance}"
                )
            
            # Deduct credits
            user.credit_balance -= cost
            user.updated_at = datetime.utcnow()
            
            # Log transaction
            transaction = CreditTransaction(
                user_id=user.id,
                amount=-cost,  # Negative for usage
                transaction_type='usage',
                operation=operation,
                description=description or f"Credit usage for {operation}",
                extra_data=extra_data or {}
            )
            db.add(transaction)
            
            await db.commit()
            
            logger.info(
                f"Deducted {cost} credits from user {user_id} for {operation}. "
                f"New balance: {user.credit_balance}"
            )
            
            return True
    
    async def add_credits(
        self,
        db: AsyncSession,
        user_id: str,
        amount: int,
        transaction_type: str = 'purchase',
        description: Optional[str] = None,
        stripe_session_id: Optional[str] = None,
        stripe_payment_intent_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add credits to user account.
        
        Args:
            db: Database session
            user_id: User ID
            amount: Credits to add
            transaction_type: Type of transaction ('purchase', 'refund', 'adjustment')
            description: Transaction description
            stripe_session_id: Stripe session ID
            stripe_payment_intent_id: Stripe payment intent ID
            extra_data: Additional metadata
            
        Returns:
            True if successful
        """
        async with db.begin():
            # Lock user row for update
            result = await db.execute(
                select(User).where(User.id == user_id).with_for_update()
            )
            user = result.scalar_one_or_none()
            
            if user is None:
                raise ValueError(f"User {user_id} not found")
            
            # Add credits
            user.credit_balance += amount
            user.updated_at = datetime.utcnow()
            
            # Log transaction
            transaction = CreditTransaction(
                user_id=user.id,
                amount=amount,  # Positive for addition
                transaction_type=transaction_type,
                description=description or f"Added {amount} credits via {transaction_type}",
                stripe_session_id=stripe_session_id,
                stripe_payment_intent_id=stripe_payment_intent_id,
                extra_data=extra_data or {}
            )
            db.add(transaction)
            
            await db.commit()
            
            logger.info(
                f"Added {amount} credits to user {user_id} via {transaction_type}. "
                f"New balance: {user.credit_balance}"
            )
            
            return True
    
    async def refund_credits(
        self,
        db: AsyncSession,
        user_id: str,
        amount: int,
        reason: str,
        original_operation: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Refund credits to user account (e.g., for failed API operations).
        
        Args:
            db: Database session
            user_id: User ID
            amount: Credits to refund
            reason: Refund reason
            original_operation: Original operation that failed
            extra_data: Additional metadata
            
        Returns:
            True if successful
        """
        return await self.add_credits(
            db=db,
            user_id=user_id,
            amount=amount,
            transaction_type='refund',
            description=f"Refund: {reason}",
            extra_data={
                **(extra_data or {}),
                'refund_reason': reason,
                'original_operation': original_operation
            }
        )
    
    async def get_transaction_history(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CreditTransaction]:
        """
        Get user's credit transaction history.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip
            transaction_type: Filter by transaction type
            start_date: Filter transactions from this date
            end_date: Filter transactions until this date
            
        Returns:
            List of credit transactions
        """
        query = select(CreditTransaction).where(CreditTransaction.user_id == user_id)
        
        # Apply filters
        if transaction_type:
            query = query.where(CreditTransaction.transaction_type == transaction_type)
        
        if start_date:
            query = query.where(CreditTransaction.created_at >= start_date)
        
        if end_date:
            query = query.where(CreditTransaction.created_at <= end_date)
        
        # Order by most recent first
        query = query.order_by(desc(CreditTransaction.created_at))
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_usage_summary(
        self,
        db: AsyncSession,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get usage summary for the last N days.
        
        Args:
            db: Database session
            user_id: User ID
            days: Number of days to include in summary
            
        Returns:
            Usage summary dictionary
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get total credits used
        credits_used_result = await db.execute(
            select(func.sum(CreditTransaction.amount))
            .where(
                and_(
                    CreditTransaction.user_id == user_id,
                    CreditTransaction.transaction_type == 'usage',
                    CreditTransaction.created_at >= start_date
                )
            )
        )
        total_credits_used = abs(credits_used_result.scalar() or 0)
        
        # Get total credits purchased
        credits_purchased_result = await db.execute(
            select(func.sum(CreditTransaction.amount))
            .where(
                and_(
                    CreditTransaction.user_id == user_id,
                    CreditTransaction.transaction_type == 'purchase',
                    CreditTransaction.created_at >= start_date
                )
            )
        )
        total_credits_purchased = credits_purchased_result.scalar() or 0
        
        # Get usage by operation type
        usage_by_operation = await db.execute(
            select(
                CreditTransaction.operation,
                func.sum(CreditTransaction.amount).label('total_used'),
                func.count(CreditTransaction.id).label('count')
            )
            .where(
                and_(
                    CreditTransaction.user_id == user_id,
                    CreditTransaction.transaction_type == 'usage',
                    CreditTransaction.created_at >= start_date
                )
            )
            .group_by(CreditTransaction.operation)
        )
        
        operation_stats = {}
        for row in usage_by_operation:
            if row.operation:
                operation_stats[row.operation] = {
                    'credits_used': abs(row.total_used),
                    'operation_count': row.count
                }
        
        return {
            'period_days': days,
            'start_date': start_date.isoformat(),
            'end_date': datetime.utcnow().isoformat(),
            'total_credits_used': total_credits_used,
            'total_credits_purchased': total_credits_purchased,
            'net_credit_change': total_credits_purchased - total_credits_used,
            'usage_by_operation': operation_stats
        }
    
    async def check_low_credit_warning(
        self,
        db: AsyncSession,
        user_id: str,
        warning_threshold: int = 10
    ) -> bool:
        """
        Check if user has low credit balance.
        
        Args:
            db: Database session
            user_id: User ID
            warning_threshold: Credit threshold for warning
            
        Returns:
            True if user has low credits
        """
        balance = await self.get_user_balance(db, user_id)
        return balance <= warning_threshold
    
    async def calculate_operation_cost(
        self,
        operation: str,
        **kwargs
    ) -> int:
        """
        Calculate cost for an operation based on type and parameters.
        
        Args:
            operation: Operation type
            **kwargs: Operation parameters
            
        Returns:
            Credit cost for the operation
        """
        # Cost table for different operations
        OPERATION_COSTS = {
            'asin_query': 1,
            'fnsku_conversion': 2,
            'bulk_asin_query': lambda count: max(1, count // 10),  # Bulk discount
            'premium_data': 3,
        }
        
        if operation in OPERATION_COSTS:
            cost = OPERATION_COSTS[operation]
            if callable(cost):
                # Dynamic cost calculation
                return cost(**kwargs)
            return cost
        
        # Default cost for unknown operations
        return 1


# Global credit service instance
credit_service = CreditService()