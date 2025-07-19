"""
Pydantic schemas for authentication and user management.
"""
import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    """Schema for user creation."""
    password: str = Field(..., min_length=8, max_length=100)
    supabase_user_id: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for user updates."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    """User schema as stored in database."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    credit_balance: int
    supabase_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UserResponse(UserInDB):
    """User schema for API responses."""
    pass


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenData(BaseModel):
    """Schema for token data."""
    user_id: Optional[str] = None
    email: Optional[str] = None
    supabase_user_id: Optional[str] = None


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class AuthError(BaseModel):
    """Schema for authentication errors."""
    error: str
    error_description: str
    status_code: int


class UserProfile(BaseModel):
    """Schema for user profile information."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str] = None
    credit_balance: int
    is_active: bool
    created_at: datetime
    
    # Usage statistics (optional, can be computed)
    total_queries: Optional[int] = None
    total_credits_used: Optional[int] = None
    total_credits_purchased: Optional[int] = None


class SupabaseUserCreate(BaseModel):
    """Schema for creating user via Supabase."""
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class SupabaseAuthResponse(BaseModel):
    """Schema for Supabase authentication response."""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    user: dict