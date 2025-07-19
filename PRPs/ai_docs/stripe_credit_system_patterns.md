# Stripe Credit System Implementation Patterns

## Credit Purchase Flow

```python
# services/payment_service.py
async def create_checkout_session(
    user_id: str,
    credit_package: str,
    success_url: str,
    cancel_url: str
) -> dict:
    """Create Stripe checkout session for credit purchase."""
    
    CREDIT_PACKAGES = {
        "starter": {"credits": 100, "price": 1000},  # $10.00
        "professional": {"credits": 500, "price": 4500},  # $45.00
        "business": {"credits": 1000, "price": 8000},  # $80.00
        "enterprise": {"credits": 5000, "price": 35000}  # $350.00
    }
    
    package_info = CREDIT_PACKAGES.get(credit_package)
    if not package_info:
        raise ValueError("Invalid credit package")
    
    session = stripe.checkout.Session.create(
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
            'credits': package_info["credits"],
            'package': credit_package
        }
    )
    
    return {"checkout_url": session.url, "session_id": session.id}
```

## Webhook Processing Pattern

```python
# api/v1/endpoints/payments.py
@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        await handle_successful_payment(event['data']['object'], db)
    elif event['type'] == 'payment_intent.payment_failed':
        await handle_failed_payment(event['data']['object'], db)
    
    return {"status": "success"}

async def handle_successful_payment(session: dict, db: AsyncSession):
    """Process successful credit purchase."""
    user_id = session['client_reference_id']
    credits_to_add = int(session['metadata']['credits'])
    
    # Create transaction record
    transaction = CreditTransaction(
        user_id=user_id,
        amount=credits_to_add,
        transaction_type='purchase',
        stripe_session_id=session['id'],
        metadata={
            'package': session['metadata']['package'],
            'amount_paid': session['amount_total']
        }
    )
    
    # Update user credit balance atomically
    async with db.begin():
        db.add(transaction)
        user = await db.get(User, user_id)
        user.credit_balance += credits_to_add
        await db.commit()
    
    # Send confirmation email (background task)
    await send_credit_purchase_confirmation(user_id, credits_to_add)
```

## Credit Deduction Pattern

```python
# services/credit_service.py
async def deduct_credits(
    db: AsyncSession,
    user_id: str,
    operation: str,
    cost: int,
    metadata: dict = None
) -> bool:
    """Atomically deduct credits for API operation."""
    
    async with db.begin():
        # Lock user row for update
        user = await db.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = user.scalar_one()
        
        if user.credit_balance < cost:
            raise InsufficientCreditsError(
                f"Operation requires {cost} credits, but user has {user.credit_balance}"
            )
        
        # Deduct credits
        user.credit_balance -= cost
        
        # Log transaction
        transaction = CreditTransaction(
            user_id=user_id,
            amount=-cost,
            transaction_type='usage',
            operation=operation,
            metadata=metadata or {}
        )
        db.add(transaction)
        
        await db.commit()
        return True

# Usage in API endpoints
@router.post("/product/asin")
async def get_product_data(
    request: ProductRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check and deduct credits first
    credit_cost = calculate_operation_cost(request)
    await credit_service.deduct_credits(
        db, user_id, "asin_query", credit_cost,
        metadata={"asin": request.asin, "marketplace": request.marketplace}
    )
    
    try:
        # Perform API operation
        result = await amazon_service.get_product_data(request.asin)
        return result
    except Exception as e:
        # Refund credits on failure
        await credit_service.refund_credits(
            db, user_id, credit_cost, "api_failure",
            metadata={"error": str(e), "asin": request.asin}
        )
        raise HTTPException(500, "External API error")
```

## Database Models

```python
# models/models.py
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    credit_balance = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # Positive for purchase, negative for usage
    transaction_type = Column(String, nullable=False)  # 'purchase', 'usage', 'refund'
    operation = Column(String)  # 'asin_query', 'fnsku_conversion', etc.
    stripe_session_id = Column(String)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## Critical Implementation Notes

- **Atomic Operations**: Always use database transactions for credit operations
- **Idempotent Webhooks**: Store processed webhook IDs to prevent duplicates
- **Partial Refunds**: Implement credit refunds for failed API operations
- **Security**: Verify Stripe webhook signatures to prevent fraud
- **Monitoring**: Track credit usage patterns for business analytics
- **Testing**: Mock Stripe operations in tests, use test webhook endpoints