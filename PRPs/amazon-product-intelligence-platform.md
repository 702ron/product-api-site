name: "Amazon Product Intelligence Platform - Production Implementation PRP"
description: |
  Comprehensive PRP for implementing a credit-based SaaS platform providing Amazon product data through REST APIs with authentication, payment processing, and external API integration.

## Goal

Build a production-ready Amazon Product Intelligence Platform - an API-first, credit-based SaaS platform that provides unified access to Amazon product intelligence through:

- **ASIN Product Data API**: Real-time Amazon product information (price, reviews, ratings, images, descriptions)
- **FNSKU to ASIN Conversion**: High-accuracy barcode conversion with confidence scoring
- **Credit Management System**: Stripe-powered prepaid credit system with multiple pricing tiers
- **User Authentication**: Supabase-based JWT authentication with Row Level Security
- **Modern Dashboard**: React-based user interface for API management and analytics

**End State**: A scalable, production-ready platform capable of handling 3,000+ requests per second with <200ms response times and 99.9% uptime.

## Why

- **Market Opportunity**: $2.1B global market for product data APIs with 14.57% CAGR growth
- **Business Value**: Credit-based pricing model generating $50/month average revenue per user
- **User Impact**: Solving fragmented, expensive, unreliable product data access for e-commerce businesses
- **Technical Excellence**: Demonstrating production-ready FastAPI architecture with modern async patterns

## What

### User-Visible Behavior

1. **User Registration & Onboarding**
   - Email/password registration with social login options
   - Free trial credits (10 credits) automatically assigned
   - Interactive dashboard tour highlighting key features

2. **Credit Purchase System**
   - Multiple credit packages (100, 500, 1000, 5000 credits)
   - Stripe checkout integration with saved payment methods
   - Real-time credit balance display with usage history

3. **Product Data API**
   - REST API endpoint for ASIN queries with comprehensive product data
   - Multiple marketplace support (US, UK, DE, JP, etc.)
   - Rate limiting with clear error responses and JSON schema

4. **FNSKU Conversion Service**
   - FNSKU input validation and high-accuracy conversion
   - Confidence scoring with fallback mechanisms
   - Bulk conversion support for efficiency

### Technical Requirements

- **API Performance**: <200ms response time for 95% of requests
- **Data Accuracy**: >99% for product information, >95% for FNSKU conversions
- **Reliability**: 99.9% uptime with graceful error handling
- **Security**: JWT authentication, rate limiting, input validation
- **Scalability**: Async architecture supporting high concurrency

### Success Criteria

- [ ] All API endpoints functional with proper authentication
- [ ] Credit system working with Stripe integration and webhook processing
- [ ] ASIN product data retrieval with caching and rate limiting
- [ ] FNSKU conversion with confidence scoring
- [ ] User dashboard with real-time credit balance and usage analytics
- [ ] Comprehensive error handling with appropriate HTTP status codes
- [ ] Test coverage >85% with both unit and integration tests
- [ ] Performance benchmarks met (<200ms API response time)
- [ ] Production deployment ready with monitoring and logging

## All Needed Context

### Documentation & References

```yaml
# MUST READ - Critical for implementation success

# FastAPI Production Patterns
- docfile: PRPs/ai_docs/fastapi_production_patterns.md
  why: Production-ready project structure, async patterns, authentication, error handling

# Stripe Credit System
- docfile: PRPs/ai_docs/stripe_credit_system_patterns.md
  why: Credit purchase flow, webhook processing, atomic credit deduction patterns

# FastAPI Official Documentation
- url: https://fastapi.tiangolo.com/tutorial/bigger-applications/
  why: Project structure and dependency injection patterns
  
- url: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
  why: JWT authentication implementation with dependencies

- url: https://fastapi.tiangolo.com/async/
  why: Proper async/await usage patterns for I/O operations

# Supabase Integration
- url: https://supabase.com/docs/guides/auth
  why: Authentication setup and JWT verification patterns
  
- url: https://supabase.com/docs/guides/database/postgres/row-level-security
  why: Database security with user isolation

- url: https://github.com/AtticusZeller/fastapi_supabase_template
  why: FastAPI + Supabase integration examples and patterns

# Stripe Documentation
- url: https://docs.stripe.com/payments/payment-intents
  why: Payment processing and checkout session creation
  
- url: https://docs.stripe.com/webhooks/quickstart
  why: Webhook handling and signature verification
  
- url: https://docs.stripe.com/billing/subscriptions/usage-based
  why: Credit-based billing patterns and usage tracking

# Amazon Product Data APIs
- url: https://webservices.amazon.com/paapi5/documentation/
  why: Official Amazon Product Advertising API for product data
  
- url: https://app.rainforestapi.com/
  why: Third-party Amazon API service with JSON responses

# Performance and Production
- url: https://github.com/zhanymkanov/fastapi-best-practices
  why: Production-ready FastAPI patterns and performance optimization
  
- url: https://loadforge.com/guides/fastapi-performance-tuning-tricks-to-enhance-speed-and-scalability
  why: Specific performance tuning for high-concurrency applications
```

### Current Codebase Tree

```bash
/Users/ronwilliams/Desktop/scripts/product_api_site/
├── .claude/
│   ├── settings.local.json     # Claude Code configuration
│   └── commands/               # 28+ development commands
├── PRPs/
│   ├── ai_docs/               # Curated documentation
│   │   ├── fastapi_production_patterns.md
│   │   └── stripe_credit_system_patterns.md
│   └── templates/             # PRP templates
├── claude_md_files/           # Framework examples
├── scripts/
│   └── prp_runner.py         # PRP execution script
├── CLAUDE.md                  # Project guidance
└── amazon-product-intelligence-platform-prd.md  # Complete requirements
```

### Desired Codebase Tree with Files to be Added

```bash
/Users/ronwilliams/Desktop/scripts/product_api_site/
├── app/                      # Main FastAPI application
│   ├── main.py              # Application entry point with CORS/middleware
│   ├── api/
│   │   ├── v1/
│   │   │   └── endpoints/
│   │   │       ├── auth.py          # Supabase authentication
│   │   │       ├── credits.py       # Credit management
│   │   │       ├── products.py      # ASIN product data
│   │   │       ├── conversion.py    # FNSKU conversion
│   │   │       └── payments.py      # Stripe webhooks
│   │   └── deps.py          # FastAPI dependencies
│   ├── core/
│   │   ├── config.py        # Pydantic settings management
│   │   ├── security.py      # JWT verification and auth
│   │   └── database.py      # Async SQLAlchemy setup
│   ├── models/              # Database models
│   │   ├── __init__.py
│   │   └── models.py        # User, CreditTransaction, etc.
│   ├── schemas/             # Pydantic request/response models
│   │   ├── __init__.py
│   │   ├── auth.py         # Authentication schemas
│   │   ├── credits.py      # Credit operation schemas
│   │   └── products.py     # Product data schemas
│   ├── services/            # Business logic layer
│   │   ├── __init__.py
│   │   ├── credit_service.py    # Credit deduction logic
│   │   ├── amazon_service.py    # External API integration
│   │   ├── fnsku_service.py     # FNSKU conversion logic
│   │   └── payment_service.py   # Stripe integration
│   ├── crud/                # Database operations
│   │   ├── __init__.py
│   │   └── crud_users.py    # User CRUD operations
│   └── tests/               # Test files
│       ├── __init__.py
│       ├── test_auth.py
│       ├── test_credits.py
│       └── test_products.py
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Local development setup
├── .env.example            # Environment variables template
└── alembic/                # Database migrations
    ├── env.py
    └── versions/
```

### Known Gotchas & Library Quirks

```python
# CRITICAL: FastAPI async patterns
# Use async functions for all I/O operations (database, HTTP requests)
async def get_product_data(asin: str):  # CORRECT
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return response.json()

# GOTCHA: Supabase JWT verification
# Must verify JWT tokens on every protected endpoint
# Use FastAPI dependency injection pattern
user_id: str = Depends(get_current_user)

# CRITICAL: Stripe webhook security
# Always verify webhook signatures to prevent fraud
try:
    event = stripe.Webhook.construct_event(
        payload, sig_header, STRIPE_WEBHOOK_SECRET
    )
except stripe.error.SignatureVerificationError:
    raise HTTPException(400, "Invalid signature")

# GOTCHA: Database transactions for credits
# Credit operations MUST be atomic to prevent race conditions
async with db.begin():
    user = await db.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    # Deduct credits here

# CRITICAL: External API rate limiting
# Amazon APIs have strict rate limits - implement backoff
@retry(attempts=3, backoff=exponential)
async def call_amazon_api():
    await rate_limiter.acquire()  # Respect rate limits
    # Make API call

# GOTCHA: Pydantic v2 differences
# Use Pydantic v2 syntax for all models
class ProductRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)  # v2 syntax
    
# CRITICAL: ASIN validation
# ASIN format: B + 9 alphanumeric characters
def validate_asin(asin: str) -> bool:
    return bool(re.match(r'^B[0-9A-Z]{9}$', asin))

# GOTCHA: FNSKU format validation  
# FNSKU format: X + 10 alphanumeric characters
def validate_fnsku(fnsku: str) -> bool:
    return bool(re.match(r'^X[0-9A-F]{10}$', fnsku))
```

## Implementation Blueprint

### Data Models and Structure

Create the core data models ensuring type safety and consistency with async SQLAlchemy.

```python
# models/models.py - Database models with proper relationships
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    credit_balance = Column(Integer, default=10, nullable=False)  # 10 free trial credits
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = relationship("CreditTransaction", back_populates="user")
    query_logs = relationship("QueryLog", back_populates="user")

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # + for purchase, - for usage
    transaction_type = Column(String, nullable=False)  # 'purchase', 'usage', 'refund'
    operation = Column(String)  # 'asin_query', 'fnsku_conversion'
    stripe_session_id = Column(String)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="transactions")

# schemas/products.py - Pydantic models for API validation
class ProductRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    asin: str = Field(..., pattern=r'^B[0-9A-Z]{9}$', description="Amazon ASIN")
    marketplace: str = Field(default="US", description="Amazon marketplace")
    include_reviews: bool = Field(default=False)
    include_offers: bool = Field(default=False)
    include_images: bool = Field(default=True)

class ProductResponse(BaseModel):
    status: Literal["success", "error"]
    credits_used: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
```

### List of Tasks to be Completed (Ordered Implementation)

```yaml
Task 1 - Project Foundation:
CREATE app/main.py:
  - FastAPI application with CORS middleware
  - Include routers for v1 API endpoints
  - Global exception handlers for custom errors
  - Startup/shutdown events for database connections

CREATE app/core/config.py:
  - Pydantic Settings for environment variables
  - Database URL, Stripe keys, Supabase configuration
  - CORS origins and security settings

CREATE app/core/database.py:
  - Async SQLAlchemy engine with connection pooling
  - Database session dependency for FastAPI
  - Connection pool configuration (size=10, max_overflow=20)

Task 2 - Database Models & Migrations:
CREATE app/models/models.py:
  - User model with UUID primary key and credit balance
  - CreditTransaction model with foreign key to users
  - QueryLog model for API usage tracking
  - Proper relationships and indexes

CREATE alembic/env.py:
  - Alembic configuration for async database migrations
  - Import all models for auto-generation

RUN alembic init and create initial migration:
  - Generate migration for User and CreditTransaction tables
  - Apply migration to create database schema

Task 3 - Authentication System:
CREATE app/core/security.py:
  - JWT token verification with Supabase
  - get_current_user dependency for protected endpoints
  - Custom authentication exceptions

CREATE app/api/v1/endpoints/auth.py:
  - POST /auth/register endpoint with Supabase user creation
  - POST /auth/login endpoint returning JWT token
  - GET /auth/me endpoint for user profile

CREATE app/schemas/auth.py:
  - UserRegister, UserLogin, UserResponse Pydantic models
  - Email validation and password requirements

Task 4 - Credit Management System:
CREATE app/services/credit_service.py:
  - async deduct_credits with atomic database transactions
  - async refund_credits for failed operations
  - get_balance and get_usage_history functions

CREATE app/api/v1/endpoints/credits.py:
  - GET /credits/balance endpoint with current balance
  - GET /credits/history endpoint with transaction history
  - POST /credits/checkout-session for Stripe integration

CREATE app/schemas/credits.py:
  - CreditBalance, TransactionHistory response models
  - CheckoutSessionRequest with credit package selection

Task 5 - Stripe Payment Integration:
CREATE app/services/payment_service.py:
  - async create_checkout_session with credit package pricing
  - Stripe client configuration with async support
  - Credit package definitions (100, 500, 1000, 5000 credits)

CREATE app/api/v1/endpoints/payments.py:
  - POST /webhooks/stripe endpoint with signature verification
  - Handle checkout.session.completed events
  - Atomic credit allocation on successful payment

Task 6 - Amazon Product Data API:
CREATE app/services/amazon_service.py:
  - async get_product_data with ASIN validation
  - HTTP client configuration with rate limiting
  - Response caching with Redis (TTL: 1 hour)
  - Retry logic with exponential backoff

CREATE app/api/v1/endpoints/products.py:
  - POST /products/asin endpoint with credit deduction
  - Input validation and marketplace support
  - Error handling with partial credit refunds

CREATE app/schemas/products.py:
  - ProductRequest with ASIN pattern validation
  - ProductResponse with comprehensive product data structure

Task 7 - FNSKU Conversion Service:
CREATE app/services/fnsku_service.py:
  - async convert_fnsku_to_asin with validation
  - Confidence scoring algorithm (0-1 scale)
  - Fallback mechanisms for failed conversions
  - Bulk conversion support with batch processing

CREATE app/api/v1/endpoints/conversion.py:
  - POST /conversion/fnsku-to-asin endpoint
  - Bulk conversion endpoint for multiple FNSKUs
  - Confidence score in response

Task 8 - API Dependencies & Middleware:
CREATE app/api/deps.py:
  - Database session dependency
  - Current user dependency with JWT verification
  - Rate limiting dependency with Redis backend

UPDATE app/main.py:
  - Add rate limiting middleware (SlowAPI)
  - Security headers middleware
  - Request/response logging middleware

Task 9 - Error Handling & Validation:
CREATE custom exception classes:
  - InsufficientCreditsError (402 status)
  - ExternalAPIError (503 status)
  - ValidationError handlers (422 status)
  - Rate limit exceeded handlers (429 status)

ADD global exception handlers to main.py:
  - Structured error responses with error codes
  - Logging for debugging without exposing internals
  - Graceful degradation for external API failures

Task 10 - Testing Infrastructure:
CREATE app/tests/ structure:
  - test_auth.py for authentication flows
  - test_credits.py for credit operations
  - test_products.py for ASIN API endpoints
  - test_payments.py for Stripe webhook handling

IMPLEMENT test fixtures:
  - Database session for testing
  - Mock user creation and authentication
  - Mock external API responses
  - Stripe webhook event mocking

Task 11 - Production Configuration:
CREATE requirements.txt:
  - FastAPI, Uvicorn, SQLAlchemy, Asyncpg
  - Stripe, Supabase, HTTPX, Redis
  - Pydantic, Alembic, Pytest dependencies

CREATE docker-compose.yml:
  - PostgreSQL database service
  - Redis cache service
  - FastAPI application service

CREATE .env.example:
  - All required environment variables with descriptions
  - Secure default values where applicable
```

### Per Task Pseudocode (Critical Implementation Details)

```python
# Task 4: Credit Service Implementation
class CreditService:
    async def deduct_credits(
        self, db: AsyncSession, user_id: str, 
        operation: str, cost: int, metadata: dict = None
    ) -> bool:
        # CRITICAL: Use database transaction with row locking
        async with db.begin():
            # Lock user row to prevent race conditions
            user = await db.execute(
                select(User).where(User.id == user_id).with_for_update()
            )
            user = user.scalar_one()
            
            # Validate sufficient credits BEFORE deduction
            if user.credit_balance < cost:
                raise InsufficientCreditsError(
                    f"Requires {cost} credits, user has {user.credit_balance}"
                )
            
            # Atomic credit deduction and transaction logging
            user.credit_balance -= cost
            transaction = CreditTransaction(
                user_id=user_id, amount=-cost, 
                transaction_type='usage', operation=operation,
                metadata=metadata or {}
            )
            db.add(transaction)
            
            await db.commit()
            return True

# Task 6: Amazon Service with Rate Limiting
class AmazonService:
    def __init__(self):
        # PATTERN: Rate limiter with Redis backend
        self.rate_limiter = AsyncRateLimiter(redis_client)
        self.http_client = httpx.AsyncClient(timeout=30)
    
    @retry(attempts=3, backoff=exponential)
    async def get_product_data(self, asin: str, marketplace: str = "US"):
        # CRITICAL: Respect external API rate limits
        await self.rate_limiter.acquire(key=f"amazon_api:{marketplace}")
        
        # PATTERN: Structured error handling with specific exceptions
        try:
            response = await self.http_client.get(
                f"{AMAZON_API_URL}/product/{asin}",
                headers={"Authorization": f"Bearer {API_KEY}"},
                params={"marketplace": marketplace}
            )
            response.raise_for_status()
            
            # GOTCHA: Cache successful responses for performance
            data = response.json()
            await self.cache_client.setex(
                f"product:{asin}:{marketplace}", 3600, json.dumps(data)
            )
            return data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ProductNotFoundError(f"Product {asin} not found")
            elif e.response.status_code == 429:
                raise RateLimitExceededError("External API rate limit")
            else:
                raise ExternalAPIError(f"API error: {e.response.status_code}")

# Task 5: Stripe Webhook Handler
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    # CRITICAL: Verify webhook signature for security
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Invalid Stripe webhook signature")
        raise HTTPException(400, "Invalid signature")
    
    # PATTERN: Idempotent webhook processing
    event_id = event['id']
    if await webhook_already_processed(db, event_id):
        return {"status": "already_processed"}
    
    # Handle successful payment
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session['client_reference_id']
        credits = int(session['metadata']['credits'])
        
        # CRITICAL: Atomic credit allocation
        async with db.begin():
            await log_webhook_processed(db, event_id)
            await add_credits_to_user(db, user_id, credits, session['id'])
            await db.commit()
    
    return {"status": "success"}
```

### Integration Points

```yaml
DATABASE:
  - migration: "CREATE UNIQUE INDEX idx_webhook_events ON webhook_logs(stripe_event_id)"
  - index: "CREATE INDEX idx_user_transactions ON credit_transactions(user_id, created_at)"
  - constraint: "ALTER TABLE users ADD CONSTRAINT credit_balance_non_negative CHECK (credit_balance >= 0)"

CONFIG:
  - add to: app/core/config.py
  - pattern: "STRIPE_WEBHOOK_SECRET = Field(..., env='STRIPE_WEBHOOK_SECRET')"
  - pattern: "AMAZON_API_KEY = Field(..., env='AMAZON_API_KEY')"
  - pattern: "REDIS_URL = Field(default='redis://localhost:6379', env='REDIS_URL')"

ROUTES:
  - add to: app/main.py
  - pattern: "app.include_router(auth_router, prefix='/api/v1/auth', tags=['auth'])"
  - pattern: "app.include_router(products_router, prefix='/api/v1/products', tags=['products'])"

MIDDLEWARE:
  - add to: app/main.py
  - pattern: "app.add_middleware(CORSMiddleware, allow_origins=['https://yourdomain.com'])"
  - pattern: "app.state.limiter = limiter  # SlowAPI rate limiting"
```

## Validation Loop

### Level 1: Syntax & Style

```bash
# Run these FIRST - fix any errors before proceeding
ruff check app/ --fix  # Auto-fix formatting and imports
mypy app/            # Type checking with strict mode
bandit -r app/       # Security scanning

# Expected: No errors. If errors, READ the error message and fix the root cause.
# Common issues: Missing type hints, unused imports, SQL injection risks
```

### Level 2: Unit Tests

```python
# CREATE comprehensive test suite covering all functionality
# app/tests/test_credits.py
async def test_credit_deduction_success():
    """Test successful credit deduction with sufficient balance."""
    user = await create_test_user(credit_balance=100)
    result = await credit_service.deduct_credits(
        db, user.id, "asin_query", 10
    )
    assert result is True
    
    # Verify balance updated
    updated_user = await db.get(User, user.id)
    assert updated_user.credit_balance == 90

async def test_insufficient_credits_error():
    """Test error handling for insufficient credits."""
    user = await create_test_user(credit_balance=5)
    
    with pytest.raises(InsufficientCreditsError) as exc_info:
        await credit_service.deduct_credits(
            db, user.id, "asin_query", 10
        )
    
    assert "Requires 10 credits" in str(exc_info.value)
    
    # Verify balance unchanged
    updated_user = await db.get(User, user.id)
    assert updated_user.credit_balance == 5

async def test_stripe_webhook_processing():
    """Test Stripe webhook handles successful payment."""
    webhook_payload = create_test_checkout_session_event(
        user_id="test-user", credits=100
    )
    
    response = await test_client.post(
        "/api/v1/webhooks/stripe",
        content=webhook_payload,
        headers={"stripe-signature": generate_test_signature(webhook_payload)}
    )
    
    assert response.status_code == 200
    
    # Verify credits added
    user = await db.get(User, "test-user")
    assert user.credit_balance == 110  # 10 initial + 100 purchased

async def test_asin_product_data_retrieval():
    """Test ASIN product data endpoint with authentication."""
    user = await create_authenticated_user(credit_balance=50)
    
    with mock.patch('app.services.amazon_service.get_product_data') as mock_api:
        mock_api.return_value = {"title": "Test Product", "price": 29.99}
        
        response = await test_client.post(
            "/api/v1/products/asin",
            json={"asin": "B07ZPKCJ6X", "marketplace": "US"},
            headers={"Authorization": f"Bearer {user.jwt_token}"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["credits_used"] == 1
    assert "Test Product" in data["data"]["title"]
```

```bash
# Run and iterate until all tests pass
uv run pytest app/tests/ -v --cov=app --cov-report=html

# Expected: >85% test coverage with all tests passing
# If failing: Analyze failure, fix code logic, re-run tests
# Never mock to pass tests - fix the underlying issue
```

### Level 3: Integration Tests

```bash
# Start the complete system for integration testing
docker-compose up -d  # Database, Redis, and other services
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test complete user flow end-to-end
# 1. User Registration
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "SecurePass123!"}'

# Expected: {"status": "success", "user": {...}, "access_token": "..."}

# 2. Credit Purchase Flow
curl -X POST http://localhost:8000/api/v1/credits/checkout-session \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"package": "starter", "success_url": "...", "cancel_url": "..."}'

# Expected: {"checkout_url": "https://checkout.stripe.com/...", "session_id": "..."}

# 3. Product Data Query
curl -X POST http://localhost:8000/api/v1/products/asin \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"asin": "B07ZPKCJ6X", "marketplace": "US"}'

# Expected: {"status": "success", "credits_used": 1, "data": {...}}

# 4. FNSKU Conversion
curl -X POST http://localhost:8000/api/v1/conversion/fnsku-to-asin \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"fnsku": "X0001ABCDE"}'

# Expected: {"status": "success", "credits_used": 2, "data": {"asin": "...", "confidence": 0.95}}

# 5. Credit Balance Check
curl -X GET http://localhost:8000/api/v1/credits/balance \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Expected: {"balance": 7, "transactions": [...]}

# If any endpoint returns error: Check logs at logs/app.log for detailed stack trace
```

### Level 4: Performance & Security Validation

```bash
# Load Testing with Artillery
artillery run --config load-tests/config.yml load-tests/api-endpoints.yml

# Expected: 
# - P95 response time < 200ms
# - 99.9% success rate
# - Handle 1000+ concurrent users

# Security Testing
npm audit --audit-level high
safety check --full-report
bandit -r app/ -ll

# Expected: No high-severity vulnerabilities

# Database Performance Testing
python scripts/benchmark_credit_operations.py

# Expected:
# - Credit deduction: <10ms per operation
# - Concurrent user handling without race conditions
# - Database connection pool efficiency >80%

# API Documentation Generation
uv run python -c "
import json
from app.main import app
with open('api-docs.json', 'w') as f:
    json.dump(app.openapi(), f, indent=2)
print('API documentation generated')
"

# Stripe Webhook Testing (use Stripe CLI)
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe

# Expected: Successful webhook delivery and processing
```

## Final Validation Checklist

- [ ] All tests pass: `uv run pytest app/tests/ -v` (>85% coverage)
- [ ] No linting errors: `uv run ruff check app/`
- [ ] No type errors: `uv run mypy app/`
- [ ] Security scan clean: `bandit -r app/ -ll`
- [ ] Integration tests successful: All curl commands return expected responses
- [ ] Performance benchmarks met: <200ms P95 response time
- [ ] Stripe webhooks working: Payment events processed correctly
- [ ] Database migrations applied: `alembic upgrade head`
- [ ] Credit system functional: Deduction, refunds, and balance tracking
- [ ] Authentication working: JWT verification and protected endpoints
- [ ] External API integration: Amazon product data retrieval with caching
- [ ] FNSKU conversion operational: Confidence scoring and validation
- [ ] Error handling comprehensive: Appropriate HTTP status codes and messages
- [ ] Rate limiting active: API protection against abuse
- [ ] Logging configured: Structured logs without sensitive data exposure
- [ ] Environment configuration: All secrets properly configured
- [ ] Docker setup working: `docker-compose up -d` starts all services

---

## Confidence Score: 9/10

This PRP provides comprehensive context for one-pass implementation success through:

✅ **Complete Architecture Blueprint**: Production-ready FastAPI structure with async patterns
✅ **External API Integration**: Detailed patterns for Amazon, Stripe, and Supabase
✅ **Security Implementation**: JWT authentication, webhook verification, rate limiting  
✅ **Comprehensive Testing**: Unit, integration, performance, and security validation
✅ **Production Considerations**: Error handling, logging, monitoring, deployment
✅ **Detailed Implementation**: Task-by-task breakdown with pseudocode and gotchas
✅ **Reference Documentation**: Created FastAPI and Stripe pattern guides in ai_docs/
✅ **Validation Loops**: Executable commands for syntax, tests, integration, and performance

The implementation blueprint includes critical details like database transactions for credit operations, async patterns for external APIs, Stripe webhook security, and comprehensive error handling. All necessary URLs and documentation are provided for the AI agent to successfully implement the platform in a single pass.

---

## Anti-Patterns to Avoid

- ❌ Don't skip JWT verification on protected endpoints - security critical
- ❌ Don't use sync functions in async context - breaks FastAPI performance  
- ❌ Don't ignore Stripe webhook signature verification - prevents fraud
- ❌ Don't skip database transactions for credit operations - causes race conditions
- ❌ Don't hardcode API keys or secrets - use environment variables
- ❌ Don't catch all exceptions without specificity - makes debugging impossible
- ❌ Don't skip rate limiting on external APIs - causes service disruption
- ❌ Don't mock successful tests - fix actual implementation issues
- ❌ Don't skip database migrations - creates production deployment issues
- ❌ Don't log sensitive data (API keys, JWT tokens) - security violation