"""
Tests for authentication endpoints and security functionality.
"""
import pytest
from unittest.mock import patch, Mock
from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import create_access_token, verify_supabase_jwt, get_current_active_user
from app.core.exceptions import AuthenticationError
from app.models.models import User


class TestAuthEndpoints:
    """Test authentication API endpoints."""
    
    def test_register_success(self, client: TestClient):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "password": "securepassword123",
            "full_name": "New User"
        }
        
        with patch('app.api.v1.endpoints.auth.supabase_client') as mock_supabase:
            mock_supabase.auth.sign_up.return_value.user = Mock(id="new-user-id")
            
            response = client.post("/api/v1/auth/register", json=user_data)
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert "user" in data
            assert data["user"]["email"] == user_data["email"]
            assert "access_token" in data
    
    def test_register_duplicate_email(self, client: TestClient):
        """Test registration with duplicate email."""
        user_data = {
            "email": "test@example.com",  # Already exists in test fixtures
            "password": "securepassword123",
            "full_name": "Duplicate User"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "already registered" in data["error"]["message"].lower()
    
    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email format."""
        user_data = {
            "email": "invalid-email",
            "password": "securepassword123",
            "full_name": "Invalid User"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_login_success(self, client: TestClient, test_user: User):
        """Test successful user login."""
        login_data = {
            "email": test_user.email,
            "password": "correctpassword"
        }
        
        with patch('app.api.v1.endpoints.auth.supabase_client') as mock_supabase:
            mock_supabase.auth.sign_in_with_password.return_value.user = Mock(
                id=test_user.supabase_user_id
            )
            mock_supabase.auth.sign_in_with_password.return_value.session = Mock(
                access_token="test-token"
            )
            
            response = client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "access_token" in data
            assert data["user"]["email"] == test_user.email
    
    def test_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        with patch('app.api.v1.endpoints.auth.supabase_client') as mock_supabase:
            mock_supabase.auth.sign_in_with_password.side_effect = Exception("Invalid credentials")
            
            response = client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_missing_fields(self, client: TestClient):
        """Test login with missing required fields."""
        login_data = {"email": "test@example.com"}  # Missing password
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_logout_success(self, client: TestClient, auth_headers: dict):
        """Test successful logout."""
        with patch('app.api.v1.endpoints.auth.supabase_client') as mock_supabase:
            mock_supabase.auth.sign_out.return_value = None
            
            response = client.post("/api/v1/auth/logout", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "Successfully logged out"
    
    def test_logout_without_auth(self, client: TestClient):
        """Test logout without authentication."""
        response = client.post("/api/v1/auth/logout")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_token_success(self, client: TestClient, auth_headers: dict):
        """Test successful token refresh."""
        with patch('app.api.v1.endpoints.auth.supabase_client') as mock_supabase:
            mock_supabase.auth.refresh_session.return_value.session = Mock(
                access_token="new-token",
                refresh_token="new-refresh-token"
            )
            
            response = client.post("/api/v1/auth/refresh", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "access_token" in data
    
    def test_get_profile_success(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test successful profile retrieval."""
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.get("/api/v1/auth/profile", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["email"] == test_user.email
            assert data["credit_balance"] == test_user.credit_balance
    
    def test_get_profile_unauthorized(self, client: TestClient):
        """Test profile retrieval without authentication."""
        response = client.get("/api/v1/auth/profile")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_update_profile_success(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test successful profile update."""
        update_data = {"full_name": "Updated Name"}
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.put("/api/v1/auth/profile", json=update_data, headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["full_name"] == update_data["full_name"]


class TestJWTSecurity:
    """Test JWT token functionality."""
    
    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_valid_token(self, mock_supabase_jwt_payload):
        """Test verification of valid JWT token."""
        with patch('app.core.security.jwt.decode', return_value=mock_supabase_jwt_payload):
            payload = verify_jwt_token("valid-token")
            
            assert payload["sub"] == mock_supabase_jwt_payload["sub"]
            assert payload["email"] == mock_supabase_jwt_payload["email"]
    
    def test_verify_invalid_token(self):
        """Test verification of invalid JWT token."""
        with patch('app.core.security.jwt.decode', side_effect=Exception("Invalid token")):
            with pytest.raises(AuthenticationError):
                verify_jwt_token("invalid-token")
    
    def test_verify_expired_token(self):
        """Test verification of expired JWT token."""
        expired_payload = {
            "sub": "user123",
            "exp": 1609459200  # January 1, 2021 (expired)
        }
        
        with patch('app.core.security.jwt.decode', return_value=expired_payload):
            with pytest.raises(AuthenticationError):
                verify_jwt_token("expired-token")


class TestUserAuthentication:
    """Test user authentication flow."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, async_session, test_user: User, mock_supabase_jwt_payload):
        """Test successful current user retrieval."""
        mock_supabase_jwt_payload["sub"] = test_user.supabase_user_id
        
        with patch('app.core.security.verify_jwt_token', return_value=mock_supabase_jwt_payload):
            from app.core.security import get_current_user
            
            user = await get_current_user("valid-token", async_session)
            
            assert user.id == test_user.id
            assert user.email == test_user.email
    
    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self, async_session, mock_supabase_jwt_payload):
        """Test current user retrieval with non-existent user."""
        mock_supabase_jwt_payload["sub"] = "non-existent-user-id"
        
        with patch('app.core.security.verify_jwt_token', return_value=mock_supabase_jwt_payload):
            from app.core.security import get_current_user, UserNotFoundError
            
            with pytest.raises(UserNotFoundError):
                await get_current_user("valid-token", async_session)
    
    @pytest.mark.asyncio
    async def test_get_current_active_user_success(self, async_session, test_user: User):
        """Test successful active user retrieval."""
        with patch('app.core.security.get_current_user', return_value=test_user):
            from app.core.security import get_current_active_user
            
            user = await get_current_active_user("valid-token", async_session)
            
            assert user.id == test_user.id
            assert user.is_active is True
    
    @pytest.mark.asyncio
    async def test_get_current_active_user_inactive(self, async_session, test_user: User):
        """Test active user retrieval with inactive user."""
        test_user.is_active = False
        
        with patch('app.core.security.get_current_user', return_value=test_user):
            from app.core.security import get_current_active_user, AuthenticationError
            
            with pytest.raises(AuthenticationError):
                await get_current_active_user("valid-token", async_session)


class TestPasswordValidation:
    """Test password validation functionality."""
    
    def test_strong_password(self, client: TestClient):
        """Test registration with strong password."""
        user_data = {
            "email": "strong@example.com",
            "password": "StrongPass123!",
            "full_name": "Strong User"
        }
        
        with patch('app.api.v1.endpoints.auth.supabase_client') as mock_supabase:
            mock_supabase.auth.sign_up.return_value.user = Mock(id="strong-user-id")
            
            response = client.post("/api/v1/auth/register", json=user_data)
            
            assert response.status_code == status.HTTP_201_CREATED
    
    def test_weak_password(self, client: TestClient):
        """Test registration with weak password."""
        user_data = {
            "email": "weak@example.com",
            "password": "123",
            "full_name": "Weak User"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAuthenticationHeaders:
    """Test authentication header handling."""
    
    def test_valid_authorization_header(self, client: TestClient, test_user: User):
        """Test valid Authorization header format."""
        headers = {"Authorization": "Bearer valid-token"}
        
        with patch('app.core.security.get_current_active_user', return_value=test_user):
            response = client.get("/api/v1/auth/profile", headers=headers)
            
            assert response.status_code == status.HTTP_200_OK
    
    def test_invalid_authorization_header_format(self, client: TestClient):
        """Test invalid Authorization header format."""
        headers = {"Authorization": "InvalidFormat token"}
        
        response = client.get("/api/v1/auth/profile", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_missing_authorization_header(self, client: TestClient):
        """Test missing Authorization header."""
        response = client.get("/api/v1/auth/profile")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_empty_authorization_header(self, client: TestClient):
        """Test empty Authorization header."""
        headers = {"Authorization": ""}
        
        response = client.get("/api/v1/auth/profile", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED