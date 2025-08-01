"""
Application configuration management using Pydantic Settings.
"""
import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "Amazon Product Intelligence Platform"
    version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Security
    secret_key: str = Field(default="dev-secret-key", env="JWT_SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./test.db", env="DATABASE_URL")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    
    # Stripe
    stripe_publishable_key: str = Field(default="pk_test_placeholder", env="STRIPE_PUBLISHABLE_KEY")
    stripe_secret_key: str = Field(default="sk_test_placeholder", env="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="whsec_placeholder", env="STRIPE_WEBHOOK_SECRET")
    
    # External APIs
    amazon_api_key: str = Field(default="placeholder-api-key", env="AMAZON_API_KEY")
    amazon_api_url: str = Field(default="https://api.asindataapi.com/request", env="AMAZON_API_URL")
    
    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:3001,https://yourdomain.com",
        env="CORS_ORIGINS"
    )
    
    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(',')]
    
    # Rate Limiting
    rate_limit_default: str = Field(default="1000/minute", env="RATE_LIMIT_DEFAULT")
    rate_limit_auth: str = Field(default="100/minute", env="RATE_LIMIT_AUTH")
    rate_limit_external_api: str = Field(default="60/minute", env="RATE_LIMIT_EXTERNAL_API")
    
    # Admin Configuration
    admin_session_timeout: int = Field(default=3600, env="ADMIN_SESSION_TIMEOUT")  # 1 hour
    admin_audit_retention_days: int = Field(default=365, env="ADMIN_AUDIT_RETENTION_DAYS")  # 1 year
    admin_max_failed_login_attempts: int = Field(default=5, env="ADMIN_MAX_FAILED_LOGIN_ATTEMPTS")
    admin_lockout_duration_minutes: int = Field(default=30, env="ADMIN_LOCKOUT_DURATION_MINUTES")
    admin_require_2fa: bool = Field(default=False, env="ADMIN_REQUIRE_2FA")
    admin_password_min_length: int = Field(default=12, env="ADMIN_PASSWORD_MIN_LENGTH")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()