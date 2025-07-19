"""
Tests for FNSKU to ASIN conversion functionality.
"""
import pytest
from unittest.mock import patch, Mock, AsyncMock
from fastapi import status
from fastapi.testclient import TestClient

from app.services.fnsku_service import FnskuService, FnskuFormatError, ConversionFailedError
from app.models.models import User, FnskuCache
from app.schemas.conversion import (
    ConversionResult, ConversionConfidence, ConversionMethod,
    FnskuValidationResult
)


class TestConversionEndpoints:
    """Test FNSKU conversion API endpoints."""
    
    def test_convert_fnsku_to_asin_success(self, client: TestClient, auth_headers: dict, test_user: User, sample_conversion_data: dict):
        """Test successful FNSKU to ASIN conversion."""
        request_data = {
            "fnsku": "X001ABC123",
            "marketplace": "US",
            "use_cache": True,
            "verify_asin": True
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            with patch('app.services.fnsku_service.fnsku_service.convert_fnsku_to_asin') as mock_convert:
                mock_result = ConversionResult(**sample_conversion_data)
                mock_convert.return_value = mock_result
                
                response = client.post("/api/v1/conversion/fnsku-to-asin", json=request_data, headers=auth_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == "success"
                assert data["conversion"]["fnsku"] == request_data["fnsku"]
                assert data["conversion"]["success"] is True
                assert data["credits_used"] > 0
    
    def test_convert_fnsku_invalid_format(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test FNSKU conversion with invalid format."""
        request_data = {
            "fnsku": "invalid",
            "marketplace": "US"
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            with patch('app.services.fnsku_service.fnsku_service.convert_fnsku_to_asin') as mock_convert:
                mock_convert.side_effect = FnskuFormatError("Invalid FNSKU format")
                
                response = client.post("/api/v1/conversion/fnsku-to-asin", json=request_data, headers=auth_headers)
                
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                data = response.json()
                assert "invalid" in data["error"]["message"].lower()
    
    def test_convert_fnsku_conversion_failed(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test FNSKU conversion failure."""
        request_data = {
            "fnsku": "X001ABC123",
            "marketplace": "US"
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            with patch('app.services.fnsku_service.fnsku_service.convert_fnsku_to_asin') as mock_convert:
                mock_convert.side_effect = ConversionFailedError("All conversion strategies failed")
                
                response = client.post("/api/v1/conversion/fnsku-to-asin", json=request_data, headers=auth_headers)
                
                assert response.status_code == status.HTTP_404_NOT_FOUND
                data = response.json()
                assert "failed" in data["error"]["message"].lower()
    
    def test_convert_fnsku_insufficient_credits(self, client: TestClient, auth_headers: dict, test_user_no_credits: User):
        """Test FNSKU conversion with insufficient credits."""
        request_data = {
            "fnsku": "X001ABC123",
            "marketplace": "US"
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user_no_credits):
            response = client.post("/api/v1/conversion/fnsku-to-asin", json=request_data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
            data = response.json()
            assert "insufficient" in data["error"]["message"].lower()
    
    def test_bulk_convert_fnskus_success(self, client: TestClient, auth_headers: dict, test_user: User, sample_conversion_data: dict):
        """Test successful bulk FNSKU conversion."""
        request_data = {
            "fnskus": ["X001ABC123", "X002DEF456", "X003GHI789"],
            "marketplace": "US",
            "use_cache": True
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            with patch('app.services.fnsku_service.fnsku_service.bulk_convert_fnskus') as mock_bulk_convert:
                mock_results = [ConversionResult(**sample_conversion_data) for _ in request_data["fnskus"]]
                mock_bulk_convert.return_value = mock_results
                
                response = client.post("/api/v1/conversion/bulk", json=request_data, headers=auth_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == "success"
                assert data["total_requested"] == len(request_data["fnskus"])
                assert data["total_successful"] == len(request_data["fnskus"])
    
    def test_bulk_convert_fnskus_partial_success(self, client: TestClient, auth_headers: dict, test_user: User, sample_conversion_data: dict):
        """Test bulk FNSKU conversion with partial success."""
        request_data = {
            "fnskus": ["X001ABC123", "INVALID456"],
            "marketplace": "US"
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            with patch('app.services.fnsku_service.fnsku_service.bulk_convert_fnskus') as mock_bulk_convert:
                # One successful, one failed
                mock_results = [
                    ConversionResult(**sample_conversion_data),
                    ConversionResult(
                        fnsku="INVALID456",
                        asin=None,
                        confidence=ConversionConfidence.NONE,
                        method=ConversionMethod.FAILED,
                        success=False,
                        cached=False,
                        conversion_time_ms=0,
                        details={},
                        error_message="Invalid FNSKU"
                    )
                ]
                mock_bulk_convert.return_value = mock_results
                
                response = client.post("/api/v1/conversion/bulk", json=request_data, headers=auth_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == "partial"
                assert data["total_successful"] == 1
                assert data["total_failed"] == 1
    
    def test_bulk_convert_too_many_fnskus(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test bulk conversion with too many FNSKUs."""
        request_data = {
            "fnskus": [f"X{i:09d}" for i in range(101)],  # 101 FNSKUs (over limit)
            "marketplace": "US"
        }
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.post("/api/v1/conversion/bulk", json=request_data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_validate_fnsku_valid(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test FNSKU validation with valid FNSKU."""
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.post("/api/v1/conversion/validate-fnsku?fnsku=X001ABC123", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["valid"] is True
            assert data["formatted_fnsku"] == "X001ABC123"
    
    def test_validate_fnsku_invalid(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test FNSKU validation with invalid FNSKU."""
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.post("/api/v1/conversion/validate-fnsku?fnsku=invalid", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["valid"] is False
            assert len(data["errors"]) > 0
    
    def test_suggest_fnsku_corrections(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test FNSKU correction suggestions."""
        request_data = {"input_value": "x001abc123"}  # Lowercase
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.post("/api/v1/conversion/suggest-fnsku", json=request_data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["original_input"] == request_data["input_value"]
            assert len(data["suggestions"]) > 0
    
    def test_get_conversion_stats(self, client: TestClient, auth_headers: dict, test_user: User, sample_fnsku_cache: FnskuCache):
        """Test conversion statistics retrieval."""
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.get("/api/v1/conversion/stats", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "total_conversions" in data
            assert "success_rate" in data
            assert "method_distribution" in data
    
    def test_get_performance_metrics(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test performance metrics retrieval."""
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.get("/api/v1/conversion/performance", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "average_conversion_time_ms" in data
            assert "cache_hit_rate" in data
            assert "method_performance" in data
    
    def test_health_check(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test conversion service health check."""
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.get("/api/v1/conversion/health", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "service_status" in data
            assert "cache_status" in data
            assert "database_status" in data


class TestFnskuService:
    """Test FNSKU service functionality."""
    
    def test_validate_fnsku_valid(self):
        """Test FNSKU validation with valid formats."""
        service = FnskuService()
        
        valid_fnskus = ["X001ABC123", "Y002DEF456", "Z999GHI789", "A000123456"]
        
        for fnsku in valid_fnskus:
            result = service.validate_fnsku(fnsku)
            assert result.valid is True
            assert result.formatted_fnsku == fnsku
            assert len(result.errors) == 0
    
    def test_validate_fnsku_invalid(self):
        """Test FNSKU validation with invalid formats."""
        service = FnskuService()
        
        invalid_fnskus = [
            "123456789",      # Too short
            "12345678901",    # Too long
            "X001ABC12@",     # Special character
            "x001abc123",     # Lowercase (should suggest uppercase)
            "",               # Empty
            "B001ABC123"      # Looks like ASIN
        ]
        
        for fnsku in invalid_fnskus:
            result = service.validate_fnsku(fnsku)
            assert result.valid is False
            assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_convert_fnsku_success_direct_api(self, async_session, sample_conversion_data: dict):
        """Test successful FNSKU conversion via direct API."""
        service = FnskuService()
        
        with patch.object(service, '_convert_via_direct_api') as mock_direct_api:
            mock_direct_api.return_value = ("B08N5WRWNW", 0.95, {"method": "direct_api"})
            
            with patch.object(service, '_verify_asin_exists') as mock_verify:
                mock_verify.return_value = True
                
                result = await service.convert_fnsku_to_asin(
                    db=async_session,
                    fnsku="X001ABC123",
                    marketplace="US"
                )
                
                assert result.success is True
                assert result.asin == "B08N5WRWNW"
                assert result.method == ConversionMethod.DIRECT_API
                assert result.confidence.value == "very_high"
    
    @pytest.mark.asyncio
    async def test_convert_fnsku_fallback_to_pattern_matching(self, async_session):
        """Test FNSKU conversion fallback to pattern matching."""
        service = FnskuService()
        
        with patch.object(service, '_convert_via_direct_api') as mock_direct_api:
            mock_direct_api.return_value = (None, 0.0, {"method": "direct_api"})
            
            with patch.object(service, '_convert_via_pattern_matching') as mock_pattern:
                mock_pattern.return_value = ("B08N5WRWNW", 0.8, {"method": "pattern_matching"})
                
                with patch.object(service, '_verify_asin_exists') as mock_verify:
                    mock_verify.return_value = True
                    
                    result = await service.convert_fnsku_to_asin(
                        db=async_session,
                        fnsku="X001ABC123",
                        marketplace="US"
                    )
                    
                    assert result.success is True
                    assert result.method == ConversionMethod.PATTERN_MATCHING
                    assert result.confidence.value == "high"
    
    @pytest.mark.asyncio
    async def test_convert_fnsku_cached_result(self, async_session, sample_fnsku_cache: FnskuCache):
        """Test FNSKU conversion with cached result."""
        service = FnskuService()
        
        result = await service.convert_fnsku_to_asin(
            db=async_session,
            fnsku=sample_fnsku_cache.fnsku,
            marketplace="US",
            use_cache=True
        )
        
        assert result.cached is True
        assert result.fnsku == sample_fnsku_cache.fnsku
        assert result.asin == sample_fnsku_cache.asin
        assert result.conversion_time_ms == 0  # Cached results have no conversion time
    
    @pytest.mark.asyncio
    async def test_convert_fnsku_invalid_format(self, async_session):
        """Test FNSKU conversion with invalid format."""
        service = FnskuService()
        
        with pytest.raises(FnskuFormatError):
            await service.convert_fnsku_to_asin(
                db=async_session,
                fnsku="invalid",
                marketplace="US"
            )
    
    @pytest.mark.asyncio
    async def test_convert_fnsku_all_methods_fail(self, async_session):
        """Test FNSKU conversion when all methods fail."""
        service = FnskuService()
        
        with patch.object(service, '_convert_via_direct_api') as mock_direct_api:
            mock_direct_api.return_value = (None, 0.0, {"method": "direct_api"})
            
            with patch.object(service, '_convert_via_pattern_matching') as mock_pattern:
                mock_pattern.return_value = (None, 0.0, {"method": "pattern_matching"})
                
                with pytest.raises(ConversionFailedError):
                    await service.convert_fnsku_to_asin(
                        db=async_session,
                        fnsku="X001ABC123",
                        marketplace="US"
                    )
    
    @pytest.mark.asyncio
    async def test_bulk_convert_fnskus(self, async_session):
        """Test bulk FNSKU conversion."""
        service = FnskuService()
        fnskus = ["X001ABC123", "X002DEF456", "X003GHI789"]
        
        with patch.object(service, 'convert_fnsku_to_asin') as mock_convert:
            mock_convert.side_effect = [
                ConversionResult(
                    fnsku=fnsku,
                    asin=f"B{i:09d}",
                    confidence=ConversionConfidence.HIGH,
                    method=ConversionMethod.DIRECT_API,
                    success=True,
                    cached=False,
                    conversion_time_ms=200,
                    details={}
                )
                for i, fnsku in enumerate(fnskus)
            ]
            
            results = await service.bulk_convert_fnskus(
                db=async_session,
                fnskus=fnskus,
                marketplace="US"
            )
            
            assert len(results) == len(fnskus)
            assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_get_conversion_stats(self, async_session, sample_fnsku_cache: FnskuCache):
        """Test conversion statistics calculation."""
        service = FnskuService()
        
        stats = await service.get_conversion_stats(async_session)
        
        assert stats.total_conversions >= 1
        assert 0 <= stats.success_rate <= 100
        assert isinstance(stats.method_distribution, dict)
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_cache(self, async_session):
        """Test cleanup of expired FNSKU cache entries."""
        service = FnskuService()
        
        # Create an expired cache entry
        from datetime import datetime, timedelta
        expired_cache = FnskuCache(
            fnsku="X999999999",
            asin="B99999999",
            confidence_score=80,
            conversion_method="direct_api",
            created_at=datetime.utcnow() - timedelta(days=5),
            last_updated=datetime.utcnow() - timedelta(days=5),
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired
            is_stale=False,
            cache_hits=0
        )
        
        async_session.add(expired_cache)
        await async_session.commit()
        
        # Clean up expired entries
        removed_count = await service.cleanup_expired_cache(async_session)
        
        assert removed_count >= 1


class TestConversionMethods:
    """Test different conversion methods."""
    
    @pytest.mark.asyncio
    async def test_direct_api_conversion(self, async_session):
        """Test direct API conversion method."""
        service = FnskuService()
        
        with patch.object(service, '_call_rainforest_api') as mock_api:
            mock_api.return_value = {"product": {"asin": "B08N5WRWNW"}}
            
            asin, confidence, details = await service._convert_via_direct_api(
                db=async_session,
                fnsku="X001ABC123",
                marketplace="US"
            )
            
            assert asin is not None
            assert confidence > 0
            assert details["method"] == "direct_api"
    
    @pytest.mark.asyncio
    async def test_pattern_matching_conversion(self, async_session):
        """Test pattern matching conversion method."""
        service = FnskuService()
        
        asin, confidence, details = await service._convert_via_pattern_matching(
            db=async_session,
            fnsku="X001ABC123"
        )
        
        # Pattern matching may or may not find a match
        assert details["method"] == "pattern_matching"
        assert "patterns_checked" in details
    
    def test_fnsku_transformation_rules(self):
        """Test FNSKU transformation rules."""
        service = FnskuService()
        
        # Test basic transformation
        transformed = service._apply_fnsku_transformations("X001ABC123")
        
        if transformed:
            assert transformed.startswith("B")
            assert len(transformed) == 10
    
    def test_asin_candidate_generation(self):
        """Test ASIN candidate generation."""
        service = FnskuService()
        
        candidate = service._generate_candidate_asin("X001ABC123", "B000000000")
        
        if candidate:
            assert candidate.startswith("B")
            assert len(candidate) == 10


class TestConversionConfidence:
    """Test conversion confidence scoring."""
    
    def test_confidence_enum_from_score(self):
        """Test confidence enum creation from numeric scores."""
        test_cases = [
            (0.0, ConversionConfidence.NONE),
            (0.1, ConversionConfidence.NONE),
            (0.3, ConversionConfidence.LOW),
            (0.5, ConversionConfidence.MEDIUM),
            (0.8, ConversionConfidence.HIGH),
            (0.95, ConversionConfidence.VERY_HIGH),
            (1.0, ConversionConfidence.VERY_HIGH)
        ]
        
        for score, expected in test_cases:
            result = ConversionConfidence.from_score(score)
            assert result == expected
    
    def test_confidence_numeric_values(self):
        """Test confidence enum numeric values."""
        confidence_values = {
            ConversionConfidence.NONE: 0.0,
            ConversionConfidence.LOW: 0.3,
            ConversionConfidence.MEDIUM: 0.55,
            ConversionConfidence.HIGH: 0.8,
            ConversionConfidence.VERY_HIGH: 0.95
        }
        
        for confidence, expected_value in confidence_values.items():
            assert confidence.numeric_value == expected_value


class TestConversionCaching:
    """Test conversion result caching."""
    
    @pytest.mark.asyncio
    async def test_cache_conversion_result(self, async_session):
        """Test caching of conversion results."""
        service = FnskuService()
        
        result = ConversionResult(
            fnsku="X001ABC123",
            asin="B08N5WRWNW",
            confidence=ConversionConfidence.HIGH,
            method=ConversionMethod.DIRECT_API,
            success=True,
            cached=False,
            conversion_time_ms=250,
            details={"method": "direct_api"}
        )
        
        success = await service._cache_conversion_result(
            db=async_session,
            fnsku=result.fnsku,
            result=result
        )
        
        assert success is True
        
        # Verify cache entry was created
        cached_result = await service._get_cached_conversion(
            db=async_session,
            fnsku=result.fnsku
        )
        
        assert cached_result is not None
        assert cached_result.fnsku == result.fnsku
        assert cached_result.asin == result.asin
    
    @pytest.mark.asyncio
    async def test_cache_failed_conversion(self, async_session):
        """Test caching of failed conversion results."""
        service = FnskuService()
        
        failed_result = ConversionResult(
            fnsku="X999999999",
            asin=None,
            confidence=ConversionConfidence.NONE,
            method=ConversionMethod.FAILED,
            success=False,
            cached=False,
            conversion_time_ms=100,
            details={},
            error_message="Conversion failed"
        )
        
        success = await service._cache_conversion_result(
            db=async_session,
            fnsku=failed_result.fnsku,
            result=failed_result
        )
        
        assert success is True
        
        # Verify failed result was cached
        cached_result = await service._get_cached_conversion(
            db=async_session,
            fnsku=failed_result.fnsku
        )
        
        assert cached_result is not None
        assert cached_result.success is False
        assert cached_result.error_message == "Conversion failed"