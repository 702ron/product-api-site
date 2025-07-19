"""
Application configuration management using Pydantic Settings.
"""
import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "Amazon Product Intelligence Platform"
    version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Supabase
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    supabase_service_key: str = Field(..., env="SUPABASE_SERVICE_KEY")
    supabase_jwt_secret: str = Field(..., env="SUPABASE_JWT_SECRET")
    
    # Stripe
    stripe_publishable_key: str = Field(..., env="STRIPE_PUBLISHABLE_KEY")
    stripe_secret_key: str = Field(..., env="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(..., env="STRIPE_WEBHOOK_SECRET")
    
    # External APIs
    amazon_api_key: str = Field(..., env="AMAZON_API_KEY")
    amazon_api_url: str = Field(default="https://api.rainforestapi.com/request", env="AMAZON_API_URL")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "https://yourdomain.com"],
        env="CORS_ORIGINS"
    )
    
    # Rate Limiting
    rate_limit_default: str = Field(default="100/minute", env="RATE_LIMIT_DEFAULT")
    rate_limit_auth: str = Field(default="10/minute", env="RATE_LIMIT_AUTH")
    rate_limit_external_api: str = Field(default="60/minute", env="RATE_LIMIT_EXTERNAL_API")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()