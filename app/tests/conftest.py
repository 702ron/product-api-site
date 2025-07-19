"""
Pytest configuration and fixtures for the Amazon Product Intelligence Platform tests.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.models import User, CreditTransaction, ProductCache, FnskuCache
from app.services.credit_service import credit_service
from app.services.amazon_service import amazon_service
from app.services.fnsku_service import fnsku_service
from app.services.payment_service import payment_service


# Test database URL (use SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async engine for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for testing."""
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
def override_get_db(async_session):
    """Override the get_db dependency for testing."""
    async def _override_get_db():
        yield async_session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(override_get_db) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest_asyncio.fixture(scope="function")
async def async_client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def test_user(async_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        credit_balance=100,
        supabase_user_id="test-supabase-id",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    return user


@pytest_asyncio.fixture(scope="function")
async def test_user_no_credits(async_session: AsyncSession) -> User:
    """Create a test user with no credits."""
    user = User(
        id=uuid.uuid4(),
        email="nocredits@example.com",
        full_name="No Credits User",
        credit_balance=0,
        supabase_user_id="test-supabase-id-nocredits",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    return user


@pytest_asyncio.fixture(scope="function")
async def admin_user(async_session: AsyncSession) -> User:
    """Create an admin test user."""
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        full_name="Admin User",
        credit_balance=1000,
        supabase_user_id="admin-supabase-id",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    return user


@pytest.fixture(scope="function")
def mock_jwt_token():
    """Mock JWT token for testing."""
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0LXN1cGFiYXNlLWlkIiwiZXhwIjoxNjc4ODg5Mzk5fQ.test_signature"


@pytest.fixture(scope="function")
def auth_headers(mock_jwt_token):
    """Authentication headers for testing."""
    return {"Authorization": f"Bearer {mock_jwt_token}"}


@pytest.fixture(scope="function")
def mock_amazon_service():
    """Mock Amazon service for testing."""
    service = Mock(spec=amazon_service)
    service.get_product_data = AsyncMock()
    service.validate_asin = AsyncMock()
    service.cleanup_expired_cache = AsyncMock()
    return service


@pytest.fixture(scope="function")
def mock_fnsku_service():
    """Mock FNSKU service for testing."""
    service = Mock(spec=fnsku_service)
    service.convert_fnsku_to_asin = AsyncMock()
    service.validate_fnsku = Mock()
    service.bulk_convert_fnskus = AsyncMock()
    service.get_conversion_stats = AsyncMock()
    return service


@pytest.fixture(scope="function")
def mock_payment_service():
    """Mock payment service for testing."""
    service = Mock(spec=payment_service)
    service.create_checkout_session = AsyncMock()
    service.verify_webhook_signature = Mock()
    service.handle_successful_payment = AsyncMock()
    service.handle_failed_payment = AsyncMock()
    service.get_package_info = Mock()
    return service


@pytest.fixture(scope="function")
def mock_credit_service():
    """Mock credit service for testing."""
    service = Mock(spec=credit_service)
    service.deduct_credits = AsyncMock()
    service.refund_credits = AsyncMock()
    service.add_credits = AsyncMock()
    service.get_credit_history = AsyncMock()
    return service


@pytest.fixture(scope="function")
def sample_product_data():
    """Sample product data for testing."""
    return {
        "asin": "B08N5WRWNW",
        "title": "Echo Dot (4th Gen) | Smart speaker with Alexa | Charcoal",
        "brand": "Amazon",
        "price": {"amount": 49.99, "currency": "USD", "formatted": "$49.99"},
        "rating": {"value": 4.7, "total_reviews": 45321},
        "images": [
            {"url": "https://example.com/image1.jpg", "variant": "main"},
            {"url": "https://example.com/image2.jpg", "variant": "additional"}
        ],
        "main_image": "https://example.com/image1.jpg",
        "description": "Meet Echo Dot - Our most popular smart speaker...",
        "features": [
            "Improved speaker quality",
            "Voice control your smart home",
            "Ready to help"
        ],
        "category": "Electronics",
        "availability": "in_stock",
        "in_stock": True,
        "marketplace": "US",
        "data_source": "rainforest_api"
    }


@pytest.fixture(scope="function")
def sample_conversion_data():
    """Sample FNSKU conversion data for testing."""
    return {
        "fnsku": "X001ABC123",
        "asin": "B08N5WRWNW",
        "confidence": "high",
        "method": "direct_api",
        "success": True,
        "cached": False,
        "conversion_time_ms": 250,
        "details": {
            "method": "direct_api",
            "api_endpoint": "amazon_product_api",
            "asin_verification": "passed"
        }
    }


@pytest_asyncio.fixture(scope="function")
async def sample_credit_transaction(async_session: AsyncSession, test_user: User) -> CreditTransaction:
    """Create a sample credit transaction."""
    transaction = CreditTransaction(
        user_id=test_user.id,
        amount=10,
        transaction_type="purchase",
        operation="credit_purchase",
        description="Test credit purchase",
        stripe_session_id="cs_test_123",
        extra_data={"package": "starter"},
        created_at=datetime.utcnow()
    )
    
    async_session.add(transaction)
    await async_session.commit()
    await async_session.refresh(transaction)
    
    return transaction


@pytest_asyncio.fixture(scope="function")
async def sample_product_cache(async_session: AsyncSession) -> ProductCache:
    """Create a sample product cache entry."""
    cache_entry = ProductCache(
        asin="B08N5WRWNW",
        marketplace="US",
        product_data={"title": "Test Product", "brand": "Test Brand"},
        data_source="rainforest_api",
        cache_key="product:B08N5WRWNW:US",
        last_updated=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=24),
        confidence_score=95,
        is_stale=False,
        created_at=datetime.utcnow()
    )
    
    async_session.add(cache_entry)
    await async_session.commit()
    await async_session.refresh(cache_entry)
    
    return cache_entry


@pytest_asyncio.fixture(scope="function")
async def sample_fnsku_cache(async_session: AsyncSession) -> FnskuCache:
    """Create a sample FNSKU cache entry."""
    cache_entry = FnskuCache(
        fnsku="X001ABC123",
        asin="B08N5WRWNW",
        confidence_score=85,
        conversion_method="direct_api",
        conversion_details={"method": "direct_api"},
        error_message=None,
        created_at=datetime.utcnow(),
        last_updated=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=72),
        is_stale=False,
        cache_hits=0
    )
    
    async_session.add(cache_entry)
    await async_session.commit()
    await async_session.refresh(cache_entry)
    
    return cache_entry


@pytest.fixture(scope="function")
def mock_stripe_session():
    """Mock Stripe checkout session for testing."""
    return {
        "id": "cs_test_123",
        "url": "https://checkout.stripe.com/test",
        "metadata": {
            "user_id": "test-user-id",
            "credits": "100",
            "package": "basic"
        },
        "payment_status": "paid",
        "amount_total": 1000  # $10.00 in cents
    }


@pytest.fixture(scope="function")
def mock_stripe_webhook_event():
    """Mock Stripe webhook event for testing."""
    return {
        "id": "evt_test_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "metadata": {
                    "user_id": "test-user-id",
                    "credits": "100"
                },
                "payment_status": "paid"
            }
        }
    }


@pytest.fixture(scope="function")
def mock_supabase_jwt_payload():
    """Mock Supabase JWT payload for testing."""
    return {
        "sub": "test-supabase-id",
        "email": "test@example.com",
        "aud": "authenticated",
        "role": "authenticated",
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
    }


# Mock external dependencies
@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch):
    """Mock external services for all tests."""
    # Mock Redis
    mock_redis = AsyncMock()
    monkeypatch.setattr("app.services.amazon_service.aioredis.from_url", lambda url: mock_redis)
    
    # Mock HTTP client
    mock_response = Mock()
    mock_response.json.return_value = {"product": {"asin": "B08N5WRWNW", "title": "Test Product"}}
    mock_response.raise_for_status.return_value = None
    
    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response
    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: mock_http_client)
    
    # Mock Stripe
    mock_stripe_session = Mock()
    mock_stripe_session.id = "cs_test_123"
    mock_stripe_session.url = "https://checkout.stripe.com/test"
    
    monkeypatch.setattr("stripe.checkout.Session.create", lambda **kwargs: mock_stripe_session)
    monkeypatch.setattr("stripe.Webhook.construct_event", lambda payload, sig, secret: {"id": "evt_test"})


# Utility functions for tests
def create_mock_user(**kwargs):
    """Create a mock user with default values."""
    defaults = {
        "id": uuid.uuid4(),
        "email": "test@example.com",
        "full_name": "Test User",
        "credit_balance": 100,
        "is_active": True
    }
    defaults.update(kwargs)
    return Mock(**defaults)


def create_test_asin():
    """Generate a valid test ASIN."""
    return "B08N5WRWNW"


def create_test_fnsku():
    """Generate a valid test FNSKU."""
    return "X001ABC123"


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as authentication related"
    )
    config.addinivalue_line(
        "markers", "payment: mark test as payment related"
    )
    config.addinivalue_line(
        "markers", "amazon_api: mark test as Amazon API related"
    )


# Coverage configuration
pytest_plugins = ["pytest_asyncio"]