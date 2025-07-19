"""
Stripe payment service for handling credit purchases and webhook processing.
"""
import logging
from typing import Dict, Any, Optional
import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.credit_service import credit_service

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.stripe_secret_key


class PaymentService:
    """Service for Stripe payment processing and credit management."""
    
    def __init__(self):
        self.stripe_client = stripe
        
        # Credit package definitions
        self.CREDIT_PACKAGES = {
            "starter": {"credits": 100, "price": 1000},  # $10.00
            "professional": {"credits": 500, "price": 4500},  # $45.00
            "business": {"credits": 1000, "price": 8000},  # $80.00
            "enterprise": {"credits": 5000, "price": 35000}  # $350.00
        }
    
    async def create_checkout_session(
        self,
        user_id: str,
        credit_package: str,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """
        Create Stripe checkout session for credit purchase.
        
        Args:
            user_id: User ID
            credit_package: Package type (starter, professional, business, enterprise)
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect after cancelled payment
            
        Returns:
            Dictionary with checkout URL and session ID
            
        Raises:
            ValueError: If invalid credit package
        """
        package_info = self.CREDIT_PACKAGES.get(credit_package)
        if not package_info:
            raise ValueError(f"Invalid credit package: {credit_package}")
        
        try:
            session = self.stripe_client.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'{package_info["credits"]} API Credits',
                            'description': f'Credit package for Amazon Product Intelligence API'
                        },
                        'unit_amount': package_info["price"],
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=user_id,
                metadata={
                    'credits': str(package_info["credits"]),
                    'package': credit_package,
                    'user_id': user_id
                },
                expires_at=int((stripe.util.utc_now() + 30 * 60))  # 30 minutes
            )
            
            logger.info(f"Created checkout session {session.id} for user {user_id}, package {credit_package}")
            
            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "package_info": package_info
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {str(e)}")
            raise ValueError(f"Failed to create checkout session: {str(e)}")
    
    async def handle_successful_payment(
        self,
        session: Dict[str, Any],
        db: AsyncSession
    ) -> bool:
        """
        Process successful credit purchase from Stripe webhook.
        
        Args:
            session: Stripe checkout session data
            db: Database session
            
        Returns:
            True if processed successfully
        """
        try:
            user_id = session['client_reference_id']
            credits_to_add = int(session['metadata']['credits'])
            package = session['metadata']['package']
            
            # Add credits to user account
            await credit_service.add_credits(
                db=db,
                user_id=user_id,
                amount=credits_to_add,
                transaction_type='purchase',
                description=f"Credit purchase: {package} package",
                stripe_session_id=session['id'],
                extra_data={
                    'package': package,
                    'amount_paid_cents': session['amount_total'],
                    'currency': session['currency'],
                    'customer_email': session.get('customer_details', {}).get('email'),
                    'payment_status': session['payment_status']
                }
            )
            
            logger.info(
                f"Successfully processed payment for user {user_id}: "
                f"+{credits_to_add} credits from {package} package"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing successful payment: {str(e)}")
            raise
    
    async def handle_failed_payment(
        self,
        payment_intent: Dict[str, Any],
        db: AsyncSession
    ) -> bool:
        """
        Process failed payment from Stripe webhook.
        
        Args:
            payment_intent: Stripe payment intent data
            db: Database session
            
        Returns:
            True if processed successfully
        """
        try:
            # Log the failed payment for monitoring
            logger.warning(
                f"Payment failed: {payment_intent['id']}, "
                f"amount: {payment_intent['amount']}, "
                f"failure_reason: {payment_intent.get('last_payment_error', {}).get('message', 'Unknown')}"
            )
            
            # Could implement additional logic here like:
            # - Sending failure notification emails
            # - Recording failure analytics
            # - Triggering retry mechanisms
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing failed payment: {str(e)}")
            raise
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """
        Verify Stripe webhook signature and parse event.
        
        Args:
            payload: Raw webhook payload
            signature: Stripe signature header
            
        Returns:
            Parsed Stripe event
            
        Raises:
            stripe.error.SignatureVerificationError: If signature is invalid
        """
        try:
            event = self.stripe_client.Webhook.construct_event(
                payload, signature, settings.stripe_webhook_secret
            )
            return event
        except ValueError:
            logger.error("Invalid webhook payload")
            raise ValueError("Invalid payload")
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid webhook signature")
            raise
    
    async def get_customer_info(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get customer information from Stripe.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            Customer information or None if not found
        """
        try:
            customer = self.stripe_client.Customer.retrieve(customer_id)
            return {
                'id': customer.id,
                'email': customer.email,
                'name': customer.name,
                'created': customer.created
            }
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving customer {customer_id}: {str(e)}")
            return None
    
    async def create_payment_intent(
        self,
        amount: int,
        currency: str = 'usd',
        customer_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a payment intent for custom payment flows.
        
        Args:
            amount: Amount in cents
            currency: Currency code
            customer_id: Stripe customer ID
            metadata: Additional metadata
            
        Returns:
            Payment intent data
        """
        try:
            payment_intent = self.stripe_client.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=customer_id,
                metadata=metadata or {},
                automatic_payment_methods={
                    'enabled': True,
                }
            )
            
            return {
                'id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency,
                'status': payment_intent.status
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating payment intent: {str(e)}")
            raise ValueError(f"Failed to create payment intent: {str(e)}")
    
    def get_package_info(self, package: str) -> Optional[Dict[str, Any]]:
        """
        Get credit package information.
        
        Args:
            package: Package name
            
        Returns:
            Package information or None if not found
        """
        return self.CREDIT_PACKAGES.get(package)
    
    def calculate_savings(self, package: str) -> float:
        """
        Calculate savings percentage for a package compared to starter.
        
        Args:
            package: Package name
            
        Returns:
            Savings percentage
        """
        if package == 'starter':
            return 0.0
        
        package_info = self.CREDIT_PACKAGES.get(package)
        starter_info = self.CREDIT_PACKAGES['starter']
        
        if not package_info:
            return 0.0
        
        starter_price_per_credit = starter_info['price'] / starter_info['credits']
        package_price_per_credit = package_info['price'] / package_info['credits']
        
        savings = ((starter_price_per_credit - package_price_per_credit) / starter_price_per_credit) * 100
        return max(0.0, savings)


# Global payment service instance
payment_service = PaymentService()