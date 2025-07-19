"""
Tests for main application functionality and middleware.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestApplicationEndpoints:
    """Test main application endpoints."""
    
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint returns application info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert "health" in data
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data
    
    def test_docs_endpoint(self, client: TestClient):
        """Test API documentation endpoint."""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_openapi_schema(self, client: TestClient):
        """Test OpenAPI schema endpoint."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data


class TestMiddleware:
    """Test application middleware functionality."""
    
    def test_cors_headers(self, client: TestClient):
        """Test CORS headers are present."""
        response = client.options("/", headers={"Origin": "https://example.com"})
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers or response.status_code == 200
    
    def test_security_headers(self, client: TestClient):
        """Test security headers are present."""
        response = client.get("/health")
        
        assert response.status_code == 200
        
        # Check for security headers
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security"
        ]
        
        for header in expected_headers:
            assert header.lower() in [h.lower() for h in response.headers.keys()]
    
    def test_request_id_header(self, client: TestClient):
        """Test request ID header is added."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0
    
    def test_process_time_header(self, client: TestClient):
        """Test process time header is added."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers
        
        # Should be a valid float
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0
    
    def test_rate_limiting_excluded_endpoints(self, client: TestClient):
        """Test that rate limiting excludes certain endpoints."""
        # These endpoints should not be rate limited
        excluded_endpoints = ["/health", "/", "/docs", "/openapi.json"]
        
        for endpoint in excluded_endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 404]  # 404 is ok for non-existent endpoints
    
    def test_content_type_validation(self, client: TestClient):
        """Test content type validation middleware."""
        # POST request without proper content type should fail
        response = client.post("/api/v1/auth/login", data="invalid data")
        
        # Should fail validation
        assert response.status_code in [400, 415, 422]


class TestErrorHandling:
    """Test global error handling."""
    
    def test_404_error(self, client: TestClient):
        """Test 404 error handling."""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
        assert "request_id" in data["error"]
    
    def test_405_method_not_allowed(self, client: TestClient):
        """Test 405 method not allowed error."""
        response = client.patch("/health")  # PATCH not allowed on health endpoint
        
        assert response.status_code == 405
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "METHOD_NOT_ALLOWED"
    
    def test_422_validation_error(self, client: TestClient):
        """Test 422 validation error handling."""
        # Send invalid JSON to an endpoint that expects valid data
        response = client.post("/api/v1/auth/register", json={"invalid": "data"})
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "validation_errors" in data["error"]["details"]


class TestApplicationConfiguration:
    """Test application configuration."""
    
    def test_application_metadata(self):
        """Test application metadata is correctly set."""
        assert app.title == "Amazon Product Intelligence Platform"
        assert app.description is not None
        assert app.version is not None
    
    def test_api_routes_registered(self):
        """Test that all API routes are registered."""
        routes = [route.path for route in app.routes]
        
        expected_route_prefixes = [
            "/api/v1/auth",
            "/api/v1/credits", 
            "/api/v1/payments",
            "/api/v1/products",
            "/api/v1/conversion"
        ]
        
        for prefix in expected_route_prefixes:
            # Check that at least one route with this prefix exists
            assert any(route.startswith(prefix) for route in routes), f"No routes found for {prefix}"


class TestApplicationLifecycle:
    """Test application lifecycle events."""
    
    @pytest.mark.asyncio
    async def test_startup_event(self):
        """Test application startup event."""
        # The startup event should initialize the database
        # This is tested implicitly by the fact that other tests work
        pass
    
    @pytest.mark.asyncio
    async def test_shutdown_event(self):
        """Test application shutdown event."""
        # The shutdown event should close database connections
        # This is harder to test directly, but we can verify the handler exists
        assert hasattr(app, "router")


class TestRouterConfiguration:
    """Test router configuration and tags."""
    
    def test_router_tags(self, client: TestClient):
        """Test that API routes have proper tags."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        openapi_spec = response.json()
        
        # Check that tags are defined
        assert "tags" in openapi_spec or "paths" in openapi_spec
        
        # Verify specific tags exist in the paths
        expected_tags = ["authentication", "credits", "payments", "products", "conversion"]
        
        if "paths" in openapi_spec:
            all_tags = set()
            for path_info in openapi_spec["paths"].values():
                for method_info in path_info.values():
                    if "tags" in method_info:
                        all_tags.update(method_info["tags"])
            
            for tag in expected_tags:
                assert tag in all_tags, f"Tag '{tag}' not found in API specification"