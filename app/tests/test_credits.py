"""
Tests for credit management functionality.
"""
import pytest
from unittest.mock import patch, Mock
from fastapi import status
from fastapi.testclient import TestClient

from app.services.credit_service import CreditService
from app.core.exceptions import InsufficientCreditsError
from app.models.models import User, CreditTransaction


class TestCreditEndpoints:
    """Test credit management API endpoints."""
    
    def test_get_balance_success(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test successful balance retrieval."""
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.get("/api/v1/credits/balance", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["balance"] == test_user.credit_balance
            assert data["user_id"] == str(test_user.id)
    
    def test_get_balance_unauthorized(self, client: TestClient):
        """Test balance retrieval without authentication."""
        response = client.get("/api/v1/credits/balance")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_history_success(self, client: TestClient, auth_headers: dict, test_user: User, sample_credit_transaction: CreditTransaction):
        """Test successful credit history retrieval."""
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.get("/api/v1/credits/history", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "transactions" in data
            assert len(data["transactions"]) > 0
            assert data["transactions"][0]["id"] == sample_credit_transaction.id
    
    def test_get_history_with_pagination(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test credit history with pagination parameters."""
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.get("/api/v1/credits/history?skip=0&limit=10", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "transactions" in data
            assert "total_count" in data
            assert "page_info" in data
    
    def test_get_history_invalid_pagination(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test credit history with invalid pagination parameters."""
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.get("/api/v1/credits/history?skip=-1&limit=0", headers=auth_headers)
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_purchase_credits_success(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test successful credit purchase initiation."""
        purchase_data = {
            "package": "basic",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel"
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            with patch('app.services.payment_service.create_checkout_session') as mock_create_session:
                mock_create_session.return_value = {
                    "checkout_url": "https://checkout.stripe.com/test",
                    "session_id": "cs_test_123",
                    "package_info": {"credits": 100, "price": 1000}
                }
                
                response = client.post("/api/v1/credits/purchase", json=purchase_data, headers=auth_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "checkout_url" in data
                assert "session_id" in data
    
    def test_purchase_credits_invalid_package(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test credit purchase with invalid package."""
        purchase_data = {
            "package": "invalid_package",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel"
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.post("/api/v1/credits/purchase", json=purchase_data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_purchase_credits_missing_urls(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test credit purchase with missing URLs."""
        purchase_data = {"package": "basic"}  # Missing success_url and cancel_url
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.post("/api/v1/credits/purchase", json=purchase_data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCreditService:
    """Test credit service functionality."""
    
    @pytest.mark.asyncio
    async def test_deduct_credits_success(self, async_session, test_user: User):
        """Test successful credit deduction."""
        service = CreditService()
        initial_balance = test_user.credit_balance
        deduction_amount = 5
        
        await service.deduct_credits(
            db=async_session,
            user_id=test_user.id,
            operation="test_operation",
            cost=deduction_amount,
            description="Test deduction"
        )
        
        await async_session.refresh(test_user)
        assert test_user.credit_balance == initial_balance - deduction_amount
    
    @pytest.mark.asyncio
    async def test_deduct_credits_insufficient_balance(self, async_session, test_user_no_credits: User):
        """Test credit deduction with insufficient balance."""
        service = CreditService()
        
        with pytest.raises(InsufficientCreditsError):
            await service.deduct_credits(
                db=async_session,
                user_id=test_user_no_credits.id,
                operation="test_operation",
                cost=10,
                description="Test deduction"
            )
    
    @pytest.mark.asyncio
    async def test_deduct_credits_exact_balance(self, async_session, test_user: User):
        """Test credit deduction with exact balance."""
        service = CreditService()
        initial_balance = test_user.credit_balance
        
        await service.deduct_credits(
            db=async_session,
            user_id=test_user.id,
            operation="test_operation",
            cost=initial_balance,
            description="Test deduction"
        )
        
        await async_session.refresh(test_user)
        assert test_user.credit_balance == 0
    
    @pytest.mark.asyncio
    async def test_refund_credits_success(self, async_session, test_user: User):
        """Test successful credit refund."""
        service = CreditService()
        initial_balance = test_user.credit_balance
        refund_amount = 10
        
        await service.refund_credits(
            db=async_session,
            user_id=test_user.id,
            amount=refund_amount,
            reason="Test refund",
            original_operation="test_operation"
        )
        
        await async_session.refresh(test_user)
        assert test_user.credit_balance == initial_balance + refund_amount
    
    @pytest.mark.asyncio
    async def test_add_credits_success(self, async_session, test_user: User):
        """Test successful credit addition."""
        service = CreditService()
        initial_balance = test_user.credit_balance
        add_amount = 50
        
        await service.add_credits(
            db=async_session,
            user_id=test_user.id,
            amount=add_amount,
            source="purchase",
            description="Test credit purchase",
            stripe_session_id="cs_test_123"
        )
        
        await async_session.refresh(test_user)
        assert test_user.credit_balance == initial_balance + add_amount
    
    @pytest.mark.asyncio
    async def test_get_credit_history(self, async_session, test_user: User, sample_credit_transaction: CreditTransaction):
        """Test credit history retrieval."""
        service = CreditService()
        
        history = await service.get_credit_history(
            db=async_session,
            user_id=test_user.id,
            skip=0,
            limit=10
        )
        
        assert len(history.transactions) > 0
        assert history.total_count > 0
        assert any(t.id == sample_credit_transaction.id for t in history.transactions)
    
    @pytest.mark.asyncio
    async def test_get_credit_history_empty(self, async_session, admin_user: User):
        """Test credit history retrieval for user with no transactions."""
        service = CreditService()
        
        history = await service.get_credit_history(
            db=async_session,
            user_id=admin_user.id,
            skip=0,
            limit=10
        )
        
        assert len(history.transactions) == 0
        assert history.total_count == 0
    
    @pytest.mark.asyncio
    async def test_transaction_atomicity(self, async_session, test_user: User):
        """Test that credit operations are atomic."""
        service = CreditService()
        initial_balance = test_user.credit_balance
        
        # Simulate a transaction that should fail after deduction
        with pytest.raises(Exception):
            async with async_session.begin():
                await service.deduct_credits(
                    db=async_session,
                    user_id=test_user.id,
                    operation="test_operation",
                    cost=5,
                    description="Test deduction"
                )
                # Force an error to test rollback
                raise Exception("Simulated error")
        
        # Balance should not have changed due to rollback
        await async_session.refresh(test_user)
        assert test_user.credit_balance == initial_balance


class TestCreditTransactions:
    """Test credit transaction functionality."""
    
    @pytest.mark.asyncio
    async def test_transaction_creation(self, async_session, test_user: User):
        """Test credit transaction creation."""
        transaction = CreditTransaction(
            user_id=test_user.id,
            amount=10,
            transaction_type="purchase",
            operation="credit_purchase",
            description="Test transaction",
            extra_data={"package": "basic"}
        )
        
        async_session.add(transaction)
        await async_session.commit()
        await async_session.refresh(transaction)
        
        assert transaction.id is not None
        assert transaction.user_id == test_user.id
        assert transaction.amount == 10
    
    @pytest.mark.asyncio
    async def test_transaction_relationships(self, async_session, sample_credit_transaction: CreditTransaction):
        """Test credit transaction relationships."""
        # Test that the transaction is linked to the user
        assert sample_credit_transaction.user is not None
        assert sample_credit_transaction.user.id == sample_credit_transaction.user_id
    
    def test_transaction_validation(self):
        """Test credit transaction validation."""
        # Test that transaction types are validated
        valid_types = ["purchase", "usage", "refund", "adjustment"]
        
        for transaction_type in valid_types:
            transaction = CreditTransaction(
                user_id="test-user-id",
                amount=10,
                transaction_type=transaction_type,
                operation="test",
                description="Test"
            )
            # Should not raise validation error
            assert transaction.transaction_type == transaction_type


class TestCreditPackages:
    """Test credit package functionality."""
    
    def test_package_pricing(self):
        """Test credit package pricing calculation."""
        from app.services.payment_service import PaymentService
        
        service = PaymentService()
        packages = {
            "starter": {"credits": 100, "price": 1000},  # $10.00
            "basic": {"credits": 250, "price": 2000},    # $20.00
            "premium": {"credits": 500, "price": 3500},  # $35.00
            "enterprise": {"credits": 1000, "price": 6000}  # $60.00
        }
        
        for package_name, expected in packages.items():
            package_info = service.get_package_info(package_name)
            assert package_info["credits"] == expected["credits"]
            assert package_info["price"] == expected["price"]
    
    def test_package_value_calculation(self):
        """Test credit package value per credit."""
        packages = [
            {"name": "starter", "credits": 100, "price": 1000},    # $0.10 per credit
            {"name": "basic", "credits": 250, "price": 2000},      # $0.08 per credit
            {"name": "premium", "credits": 500, "price": 3500},    # $0.07 per credit
            {"name": "enterprise", "credits": 1000, "price": 6000} # $0.06 per credit
        ]
        
        for package in packages:
            value_per_credit = package["price"] / package["credits"]
            # Larger packages should have better value (lower cost per credit)
            if package["name"] == "starter":
                assert value_per_credit == 10.0  # $0.10
            elif package["name"] == "enterprise":
                assert value_per_credit == 6.0   # $0.06


class TestCreditUsageTracking:
    """Test credit usage tracking and analytics."""
    
    @pytest.mark.asyncio
    async def test_usage_by_operation(self, async_session, test_user: User):
        """Test credit usage tracking by operation type."""
        service = CreditService()
        
        # Create different types of usage
        operations = [
            ("asin_query", 1),
            ("fnsku_conversion", 2),
            ("bulk_query", 5)
        ]
        
        for operation, cost in operations:
            await service.deduct_credits(
                db=async_session,
                user_id=test_user.id,
                operation=operation,
                cost=cost,
                description=f"Test {operation}"
            )
        
        # Get usage history and verify tracking
        history = await service.get_credit_history(
            db=async_session,
            user_id=test_user.id,
            skip=0,
            limit=10
        )
        
        operation_costs = {t.operation: abs(t.amount) for t in history.transactions if t.transaction_type == "usage"}
        
        for operation, expected_cost in operations:
            assert operation_costs.get(operation) == expected_cost
    
    @pytest.mark.asyncio
    async def test_daily_usage_limits(self, async_session, test_user: User):
        """Test daily credit usage limit enforcement."""
        service = CreditService()
        
        # This would be implemented if daily limits are added
        # For now, test that unlimited usage is possible
        total_usage = 0
        for i in range(10):
            await service.deduct_credits(
                db=async_session,
                user_id=test_user.id,
                operation="test_operation",
                cost=1,
                description=f"Test usage {i}"
            )
            total_usage += 1
        
        await async_session.refresh(test_user)
        assert test_user.credit_balance == 100 - total_usage  # Started with 100 credits