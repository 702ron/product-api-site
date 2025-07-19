"""
Stripe payment endpoints for webhook handling and payment processing.
"""
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.models import User, WebhookLog
from app.services.payment_service import payment_service
from app.services.credit_service import credit_service
from app.schemas.credits import CheckoutSessionRequest, CheckoutSessionResponse

router = APIRouter()
logger = logging.getLogger(__name__)


async def log_webhook_event(
    db: AsyncSession,
    event_id: str,
    event_type: str,
    payload: Dict[str, Any],
    status: str = 'received'
) -> bool:
    """
    Log webhook event for idempotent processing.
    
    Args:
        db: Database session
        event_id: Stripe event ID
        event_type: Event type
        payload: Event payload
        status: Processing status
        
    Returns:
        True if event is new, False if already processed
    """
    try:
        # Check if webhook already processed
        result = await db.execute(
            select(WebhookLog).where(WebhookLog.event_id == event_id)
        )
        existing_log = result.scalar_one_or_none()
        
        if existing_log:
            if existing_log.status == 'completed':
                logger.info(f"Webhook {event_id} already processed successfully")
                return False
            else:
                # Update attempts
                existing_log.attempts += 1
                existing_log.status = status
                existing_log.last_attempt_at = datetime.utcnow()
                await db.commit()
                return True
        
        # Create new webhook log
        webhook_log = WebhookLog(
            provider='stripe',
            event_id=event_id,
            event_type=event_type,
            status=status,
            attempts=1,
            payload=payload,
            last_attempt_at=datetime.utcnow()
        )
        
        db.add(webhook_log)
        await db.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error logging webhook event {event_id}: {str(e)}")
        await db.rollback()
        return True  # Proceed with processing to be safe


async def mark_webhook_completed(
    db: AsyncSession,
    event_id: str
) -> None:
    """
    Mark webhook as successfully processed.
    
    Args:
        db: Database session
        event_id: Stripe event ID
    """
    try:
        result = await db.execute(
            select(WebhookLog).where(WebhookLog.event_id == event_id)
        )
        webhook_log = result.scalar_one_or_none()
        
        if webhook_log:
            webhook_log.status = 'completed'
            await db.commit()
            
    except Exception as e:
        logger.error(f"Error marking webhook {event_id} as completed: {str(e)}")


async def mark_webhook_failed(
    db: AsyncSession,
    event_id: str,
    error_details: Dict[str, Any]
) -> None:
    """
    Mark webhook as failed with error details.
    
    Args:
        db: Database session
        event_id: Stripe event ID
        error_details: Error information
    """
    try:
        result = await db.execute(
            select(WebhookLog).where(WebhookLog.event_id == event_id)
        )
        webhook_log = result.scalar_one_or_none()
        
        if webhook_log:
            webhook_log.status = 'failed'
            webhook_log.error_details = error_details
            await db.commit()
            
    except Exception as e:
        logger.error(f"Error marking webhook {event_id} as failed: {str(e)}")


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Stripe webhook events for payment processing.
    
    Supports the following events:
    - checkout.session.completed: Successful credit purchase
    - payment_intent.payment_failed: Failed payment
    - invoice.payment_succeeded: Subscription payment (future)
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    if not sig_header:
        logger.error("Missing Stripe signature header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing signature header"
        )
    
    try:
        # Verify webhook signature
        event = payment_service.verify_webhook_signature(payload, sig_header)
        
    except ValueError:
        logger.error("Invalid webhook payload")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except Exception:
        logger.error("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    
    event_id = event['id']
    event_type = event['type']
    
    logger.info(f"Processing Stripe webhook: {event_type} ({event_id})")
    
    # Check if webhook already processed (idempotent processing)
    should_process = await log_webhook_event(
        db, event_id, event_type, event['data']
    )
    
    if not should_process:
        return {"status": "already_processed"}
    
    try:
        # Process different event types
        if event_type == 'checkout.session.completed':
            session = event['data']['object']
            
            # Ensure this is a credit purchase session
            if session.get('metadata', {}).get('credits'):
                await payment_service.handle_successful_payment(session, db)
                logger.info(f"Successfully processed checkout.session.completed for {event_id}")
            else:
                logger.warning(f"Checkout session {session['id']} is not a credit purchase")
        
        elif event_type == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            await payment_service.handle_failed_payment(payment_intent, db)
            logger.info(f"Successfully processed payment_intent.payment_failed for {event_id}")
        
        elif event_type == 'invoice.payment_succeeded':
            # Future: Handle subscription payments
            logger.info(f"Received invoice.payment_succeeded for {event_id} (not implemented)")
        
        else:
            logger.info(f"Unhandled event type: {event_type} for {event_id}")
        
        # Mark webhook as completed
        await mark_webhook_completed(db, event_id)
        
        return {"status": "success", "event_id": event_id}
        
    except Exception as e:
        logger.error(f"Error processing webhook {event_id}: {str(e)}")
        
        # Mark webhook as failed
        await mark_webhook_failed(db, event_id, {
            'error': str(e),
            'event_type': event_type
        })
        
        # Don't raise exception - return 200 to prevent Stripe retries
        # for application errors (as opposed to infrastructure errors)
        return {"status": "error", "message": "Internal processing error"}


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create Stripe checkout session for credit purchase.
    
    This replaces the placeholder implementation in the credits endpoint.
    """
    try:
        # Validate package
        package_info = payment_service.get_package_info(request.package.value)
        if not package_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid credit package: {request.package.value}"
            )
        
        # Create checkout session
        session_data = await payment_service.create_checkout_session(
            user_id=str(current_user.id),
            credit_package=request.package.value,
            success_url=request.success_url,
            cancel_url=request.cancel_url
        )
        
        return CheckoutSessionResponse(
            checkout_url=session_data["checkout_url"],
            session_id=session_data["session_id"],
            package_info=session_data["package_info"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating checkout session for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )


@router.get("/customer-portal")
async def create_customer_portal_session(
    current_user: User = Depends(get_current_active_user)
):
    """
    Create Stripe customer portal session for managing billing.
    
    Future implementation for subscription management.
    """
    # Placeholder for future customer portal integration
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Customer portal not yet implemented"
    )


@router.get("/payment-methods")
async def get_payment_methods(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get user's saved payment methods.
    
    Future implementation for saved payment methods.
    """
    # Placeholder for future payment methods management
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Payment methods management not yet implemented"
    )


@router.post("/refund")
async def create_refund(
    payment_intent_id: str,
    amount: int,
    reason: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create refund for a payment (admin functionality).
    
    Future implementation for refund processing.
    """
    # Placeholder for future refund functionality
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Refund processing not yet implemented"
    )