"""
Tests for Amazon product API functionality.
"""
import pytest
from unittest.mock import patch, Mock, AsyncMock
from fastapi import status
from fastapi.testclient import TestClient

from app.services.amazon_service import AmazonService, ProductNotFoundError, RateLimitExceededError, ExternalAPIError
from app.models.models import User, ProductCache
from app.schemas.products import ProductData, ProductPrice, ProductRating, ProductDataSource, Marketplace


class TestProductEndpoints:
    """Test product API endpoints."""
    
    def test_get_product_by_asin_success(self, client: TestClient, auth_headers: dict, test_user: User, sample_product_data: dict):
        """Test successful product retrieval by ASIN."""
        request_data = {
            "asin": "B08N5WRWNW",
            "marketplace": "US",
            "include_reviews": True,
            "include_offers": False,
            "use_cache": True
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            with patch('app.services.amazon_service.amazon_service.get_product_data') as mock_get_product:
                mock_product = ProductData(**sample_product_data)
                mock_get_product.return_value = mock_product
                
                response = client.post("/api/v1/products/asin", json=request_data, headers=auth_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == "success"
                assert data["data"]["asin"] == request_data["asin"]
                assert data["credits_used"] > 0
    
    def test_get_product_by_asin_not_found(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test product retrieval with non-existent ASIN."""
        request_data = {
            "asin": "B000000000",
            "marketplace": "US"
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            with patch('app.services.amazon_service.amazon_service.get_product_data') as mock_get_product:
                mock_get_product.side_effect = ProductNotFoundError("Product not found")
                
                response = client.post("/api/v1/products/asin", json=request_data, headers=auth_headers)
                
                assert response.status_code == status.HTTP_404_NOT_FOUND
                data = response.json()
                assert "not found" in data["error"]["message"].lower()
    
    def test_get_product_insufficient_credits(self, client: TestClient, auth_headers: dict, test_user_no_credits: User):
        """Test product retrieval with insufficient credits."""
        request_data = {
            "asin": "B08N5WRWNW",
            "marketplace": "US"
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user_no_credits):
            response = client.post("/api/v1/products/asin", json=request_data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
            data = response.json()
            assert "insufficient" in data["error"]["message"].lower()
    
    def test_get_product_invalid_asin(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test product retrieval with invalid ASIN format."""
        request_data = {
            "asin": "invalid-asin",
            "marketplace": "US"
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.post("/api/v1/products/asin", json=request_data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_get_product_rate_limit_exceeded(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test product retrieval with rate limit exceeded."""
        request_data = {
            "asin": "B08N5WRWNW",
            "marketplace": "US"
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            with patch('app.services.amazon_service.amazon_service.get_product_data') as mock_get_product:
                mock_get_product.side_effect = RateLimitExceededError("Rate limit exceeded")
                
                response = client.post("/api/v1/products/asin", json=request_data, headers=auth_headers)
                
                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    
    def test_bulk_products_success(self, client: TestClient, auth_headers: dict, test_user: User, sample_product_data: dict):
        """Test successful bulk product retrieval."""
        request_data = {
            "asins": ["B08N5WRWNW", "B07XJ8C8F5", "B084DWG2VQ"],
            "marketplace": "US",
            "include_reviews": False,
            "use_cache": True
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            with patch('app.services.amazon_service.amazon_service.get_product_data') as mock_get_product:
                mock_product = ProductData(**sample_product_data)
                mock_get_product.return_value = mock_product
                
                response = client.post("/api/v1/products/bulk", json=request_data, headers=auth_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == "success"
                assert data["total_requested"] == len(request_data["asins"])
                assert len(data["products"]) <= len(request_data["asins"])
    
    def test_bulk_products_partial_success(self, client: TestClient, auth_headers: dict, test_user: User, sample_product_data: dict):
        """Test bulk product retrieval with partial success."""
        request_data = {
            "asins": ["B08N5WRWNW", "B000000000"],  # One valid, one invalid
            "marketplace": "US"
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            with patch('app.services.amazon_service.amazon_service.get_product_data') as mock_get_product:
                def side_effect(db, asin, **kwargs):
                    if asin == "B08N5WRWNW":
                        return ProductData(**sample_product_data)
                    else:
                        raise ProductNotFoundError("Product not found")
                
                mock_get_product.side_effect = side_effect
                
                response = client.post("/api/v1/products/bulk", json=request_data, headers=auth_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == "partial"
                assert data["total_successful"] == 1
                assert len(data["errors"]) == 1
    
    def test_bulk_products_too_many_asins(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test bulk product retrieval with too many ASINs."""
        request_data = {
            "asins": [f"B{i:09d}" for i in range(101)],  # 101 ASINs (over limit)
            "marketplace": "US"
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.post("/api/v1/products/bulk", json=request_data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_validate_asin_valid(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test ASIN validation with valid ASIN."""
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.post("/api/v1/products/validate-asin?asin=B08N5WRWNW", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["valid"] is True
            assert data["formatted_asin"] == "B08N5WRWNW"
    
    def test_validate_asin_invalid(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test ASIN validation with invalid ASIN."""
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.post("/api/v1/products/validate-asin?asin=invalid", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["valid"] is False
            assert len(data["errors"]) > 0
    
    def test_get_cache_stats(self, client: TestClient, auth_headers: dict, test_user: User, sample_product_cache: ProductCache):
        """Test cache statistics retrieval."""
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.get("/api/v1/products/cache-stats", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "total_cached_products" in data
            assert "cache_hit_rate" in data
            assert "marketplaces" in data
    
    def test_cleanup_cache(self, client: TestClient, auth_headers: dict, admin_user: User):
        """Test cache cleanup endpoint."""
        with patch('app.core.security.get_current_active_user', return_value=admin_user):
            with patch('app.services.amazon_service.amazon_service.cleanup_expired_cache') as mock_cleanup:
                mock_cleanup.return_value = 5
                
                response = client.delete("/api/v1/products/cache/cleanup", headers=auth_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "cleaned up" in data["message"].lower()


class TestAmazonService:
    """Test Amazon service functionality."""
    
    @pytest.mark.asyncio
    async def test_get_product_data_success(self, async_session, sample_product_data: dict):
        """Test successful product data retrieval."""
        service = AmazonService()
        
        with patch.object(service, '_call_rainforest_api') as mock_api_call:
            mock_api_call.return_value = {"product": sample_product_data}
            
            with patch.object(service, '_parse_rainforest_data') as mock_parse:
                mock_product = ProductData(**sample_product_data)
                mock_parse.return_value = mock_product
                
                result = await service.get_product_data(
                    db=async_session,
                    asin="B08N5WRWNW",
                    marketplace="US"
                )
                
                assert result.asin == "B08N5WRWNW"
                assert result.title is not None
    
    @pytest.mark.asyncio
    async def test_get_product_data_cached(self, async_session, sample_product_cache: ProductCache):
        """Test product data retrieval from cache."""
        service = AmazonService()
        
        result = await service.get_product_data(
            db=async_session,
            asin=sample_product_cache.asin,
            marketplace=sample_product_cache.marketplace,
            use_cache=True
        )
        
        assert result.data_source == ProductDataSource.CACHE
        assert result.asin == sample_product_cache.asin
    
    @pytest.mark.asyncio
    async def test_get_product_data_not_found(self, async_session):
        """Test product data retrieval with non-existent product."""
        service = AmazonService()
        
        with patch.object(service, '_call_rainforest_api') as mock_api_call:
            mock_api_call.side_effect = ProductNotFoundError("Product not found")
            
            with pytest.raises(ProductNotFoundError):
                await service.get_product_data(
                    db=async_session,
                    asin="B000000000",
                    marketplace="US"
                )
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, async_session):
        """Test rate limiting functionality."""
        service = AmazonService()
        
        # Test that multiple rapid calls trigger rate limiting
        with patch.object(service, '_call_rainforest_api') as mock_api_call:
            mock_api_call.return_value = {"product": {"asin": "B08N5WRWNW"}}
            
            # Make multiple rapid calls
            for i in range(service.max_calls_per_minute + 1):
                if i < service.max_calls_per_minute:
                    # Should succeed
                    result = await service.get_product_data(
                        db=async_session,
                        asin=f"B{i:09d}",
                        marketplace="US",
                        use_cache=False
                    )
                else:
                    # Should trigger rate limit
                    with pytest.raises(RateLimitExceededError):
                        await service.get_product_data(
                            db=async_session,
                            asin=f"B{i:09d}",
                            marketplace="US",
                            use_cache=False
                        )
    
    @pytest.mark.asyncio
    async def test_validate_asin(self):
        """Test ASIN validation."""
        service = AmazonService()
        
        # Valid ASINs
        valid_asins = ["B08N5WRWNW", "B000000000", "B123456789"]
        for asin in valid_asins:
            assert await service.validate_asin(asin) is True
        
        # Invalid ASINs
        invalid_asins = ["123456789", "B12345678", "B1234567890", "invalid"]
        for asin in invalid_asins:
            assert await service.validate_asin(asin) is False
    
    @pytest.mark.asyncio
    async def test_cache_product(self, async_session, sample_product_data: dict):
        """Test product caching functionality."""
        service = AmazonService()
        product_data = ProductData(**sample_product_data)
        
        success = await service._cache_product(
            db=async_session,
            asin=product_data.asin,
            marketplace="US",
            product_data=product_data
        )
        
        assert success is True
        
        # Verify cache entry was created
        cached_data = await service._get_cached_product(
            db=async_session,
            asin=product_data.asin,
            marketplace="US"
        )
        
        assert cached_data is not None
        assert cached_data.asin == product_data.asin
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_cache(self, async_session):
        """Test cleanup of expired cache entries."""
        service = AmazonService()
        
        # Create an expired cache entry
        from datetime import datetime, timedelta
        expired_cache = ProductCache(
            asin="B12345678",
            marketplace="US",
            product_data={"title": "Expired Product"},
            data_source="test",
            cache_key="test:expired",
            last_updated=datetime.utcnow() - timedelta(days=2),
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired
            is_stale=False,
            created_at=datetime.utcnow() - timedelta(days=2)
        )
        
        async_session.add(expired_cache)
        await async_session.commit()
        
        # Clean up expired entries
        removed_count = await service.cleanup_expired_cache(async_session)
        
        assert removed_count >= 1


class TestProductDataParsing:
    """Test product data parsing functionality."""
    
    def test_parse_rainforest_data(self):
        """Test parsing of Rainforest API response."""
        service = AmazonService()
        
        api_response = {
            "product": {
                "asin": "B08N5WRWNW",
                "title": "Echo Dot (4th Gen)",
                "brand": "Amazon",
                "buybox_winner": {
                    "price": {
                        "currency": "USD",
                        "value": 49.99,
                        "raw": "$49.99"
                    }
                },
                "rating": 4.7,
                "ratings_total": 45321,
                "images": [
                    {"link": "https://example.com/image1.jpg"},
                    {"link": "https://example.com/image2.jpg"}
                ],
                "feature_bullets": [
                    {"text": "Improved speaker quality"},
                    {"text": "Voice control your smart home"}
                ],
                "description": "Meet Echo Dot - Our most popular smart speaker",
                "category": {"name": "Electronics"}
            }
        }
        
        result = service._parse_rainforest_data(api_response, "US")
        
        assert result.asin == "B08N5WRWNW"
        assert result.title == "Echo Dot (4th Gen)"
        assert result.brand == "Amazon"
        assert result.price.amount == 49.99
        assert result.rating.value == 4.7
        assert len(result.images) == 2
        assert len(result.features) == 2
    
    def test_parse_rainforest_data_minimal(self):
        """Test parsing of minimal Rainforest API response."""
        service = AmazonService()
        
        api_response = {
            "product": {
                "asin": "B12345678",
                "title": "Minimal Product"
            }
        }
        
        result = service._parse_rainforest_data(api_response, "US")
        
        assert result.asin == "B12345678"
        assert result.title == "Minimal Product"
        assert result.price is None
        assert result.rating is None
        assert len(result.images) == 0


class TestProductCaching:
    """Test product caching functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_calculation(self, async_session, sample_product_cache: ProductCache):
        """Test cache hit rate calculation."""
        # This would typically be calculated from query logs
        # For now, test that the endpoint returns valid data
        service = AmazonService()
        
        # Simulate cache hit
        cached_product = await service._get_cached_product(
            db=async_session,
            asin=sample_product_cache.asin,
            marketplace=sample_product_cache.marketplace
        )
        
        assert cached_product is not None
        assert cached_product.data_source == ProductDataSource.CACHE
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, async_session):
        """Test that expired cache entries are not returned."""
        from datetime import datetime, timedelta
        
        # Create an expired cache entry
        expired_cache = ProductCache(
            asin="B87654321",
            marketplace="US",
            product_data={"title": "Expired Product"},
            data_source="test",
            cache_key="test:expired",
            last_updated=datetime.utcnow() - timedelta(days=2),
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired
            is_stale=False,
            created_at=datetime.utcnow() - timedelta(days=2)
        )
        
        async_session.add(expired_cache)
        await async_session.commit()
        
        service = AmazonService()
        
        # Should return None for expired cache
        cached_product = await service._get_cached_product(
            db=async_session,
            asin=expired_cache.asin,
            marketplace=expired_cache.marketplace
        )
        
        assert cached_product is None


class TestProductValidation:
    """Test product data validation."""
    
    def test_product_data_validation(self, sample_product_data: dict):
        """Test ProductData model validation."""
        # Valid product data
        product = ProductData(**sample_product_data)
        assert product.asin == sample_product_data["asin"]
        assert product.title == sample_product_data["title"]
    
    def test_product_price_validation(self):
        """Test ProductPrice model validation."""
        # Valid price data
        price_data = {
            "currency": "USD",
            "amount": 49.99,
            "formatted": "$49.99"
        }
        
        price = ProductPrice(**price_data)
        assert price.currency == "USD"
        assert price.amount == 49.99
    
    def test_product_rating_validation(self):
        """Test ProductRating model validation."""
        # Valid rating data
        rating_data = {
            "value": 4.7,
            "total_reviews": 45321
        }
        
        rating = ProductRating(**rating_data)
        assert rating.value == 4.7
        assert rating.total_reviews == 45321