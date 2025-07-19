"""
SQLAlchemy database models for the Amazon Product Intelligence Platform.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, 
    BigInteger, JSON, Text, Boolean, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """User model with credit balance and authentication info."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    
    # Credit system
    credit_balance = Column(Integer, default=10, nullable=False)  # 10 free trial credits
    
    # Supabase user ID for authentication
    supabase_user_id = Column(String(255), unique=True, index=True, nullable=True)
    
    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    transactions = relationship("CreditTransaction", back_populates="user", cascade="all, delete-orphan")
    query_logs = relationship("QueryLog", back_populates="user", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('credit_balance >= 0', name='credit_balance_non_negative'),
    )


class CreditTransaction(Base):
    """Credit transaction log for purchases, usage, and refunds."""
    __tablename__ = "credit_transactions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Transaction details
    amount = Column(Integer, nullable=False)  # Positive for purchase/refund, negative for usage
    transaction_type = Column(String(50), nullable=False)  # 'purchase', 'usage', 'refund', 'adjustment'
    operation = Column(String(100), nullable=True)  # 'asin_query', 'fnsku_conversion', etc.
    description = Column(Text, nullable=True)
    
    # External service references
    stripe_session_id = Column(String(255), nullable=True, index=True)
    stripe_payment_intent_id = Column(String(255), nullable=True, index=True)
    
    # Additional data in JSON format
    extra_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    
    # Indexes for efficient queries
    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('purchase', 'usage', 'refund', 'adjustment')",
            name='valid_transaction_type'
        ),
    )


class QueryLog(Base):
    """API usage log for monitoring and analytics."""
    __tablename__ = "query_logs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Query details
    query_type = Column(String(100), nullable=False)  # 'asin_query', 'fnsku_conversion', 'bulk_query'
    query_input = Column(Text, nullable=False)  # ASIN, FNSKU, or bulk input
    credits_deducted = Column(Integer, nullable=False)
    
    # Response details
    status = Column(String(50), nullable=False)  # 'success', 'error', 'partial'
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    api_response_summary = Column(JSON, nullable=True)  # Summarized response data
    error_details = Column(JSON, nullable=True)  # Error information if failed
    
    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String(255), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="query_logs")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'error', 'partial')",
            name='valid_status'
        ),
        CheckConstraint('credits_deducted >= 0', name='credits_deducted_non_negative'),
    )


class WebhookLog(Base):
    """Webhook event log for idempotent processing."""
    __tablename__ = "webhook_logs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Webhook details
    provider = Column(String(50), nullable=False)  # 'stripe', 'supabase', etc.
    event_id = Column(String(255), nullable=False, unique=True, index=True)
    event_type = Column(String(100), nullable=False)
    
    # Processing status
    status = Column(String(50), nullable=False, default='received')  # 'received', 'processing', 'completed', 'failed'
    attempts = Column(Integer, default=0, nullable=False)
    last_attempt_at = Column(DateTime, nullable=True)
    
    # Event data
    payload = Column(JSON, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('received', 'processing', 'completed', 'failed')",
            name='valid_webhook_status'
        ),
        CheckConstraint('attempts >= 0', name='attempts_non_negative'),
    )


class ProductCache(Base):
    """Cache for Amazon product data to reduce external API calls."""
    __tablename__ = "product_cache"
    
    # Composite primary key
    asin = Column(String(20), primary_key=True)
    marketplace = Column(String(10), primary_key=True, default="US")
    
    # Product data
    product_data = Column(JSON, nullable=False)
    data_source = Column(String(100), nullable=False)  # 'rainforest_api', 'amazon_paapi', etc.
    
    # Cache metadata
    cache_key = Column(String(255), nullable=False, index=True)
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Quality metrics
    confidence_score = Column(Integer, nullable=True)  # 0-100 for data quality
    is_stale = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class FNSKUMapping(Base):
    """FNSKU to ASIN mapping with confidence scoring."""
    __tablename__ = "fnsku_mappings"
    
    # Primary key
    fnsku = Column(String(20), primary_key=True)
    
    # Mapping details
    asin = Column(String(20), nullable=False, index=True)
    marketplace = Column(String(10), nullable=False, default="US")
    confidence_score = Column(Integer, nullable=False)  # 0-100 confidence percentage
    
    # Product information
    product_title = Column(Text, nullable=True)
    brand = Column(String(255), nullable=True)
    category = Column(String(255), nullable=True)
    
    # Verification details
    verification_method = Column(String(100), nullable=False)  # 'manual', 'api', 'ml_model'
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String(255), nullable=True)  # User ID or system identifier
    
    # Additional source data
    source_data = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 100', name='valid_confidence_score'),
        CheckConstraint(
            "verification_method IN ('manual', 'api', 'ml_model', 'user_feedback')",
            name='valid_verification_method'
        ),
    )


class FnskuCache(Base):
    """Cache for FNSKU to ASIN conversion results to improve performance."""
    __tablename__ = "fnsku_cache"
    
    # Primary key
    fnsku = Column(String(20), primary_key=True)
    
    # Conversion result
    asin = Column(String(20), nullable=True, index=True)  # Null if conversion failed
    confidence_score = Column(Integer, nullable=False, default=0)  # 0-100 confidence percentage
    conversion_method = Column(String(100), nullable=False)  # Method used for conversion
    
    # Additional conversion details
    conversion_details = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Cache metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Cache status
    is_stale = Column(Boolean, default=False, nullable=False)
    cache_hits = Column(Integer, default=0, nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 100', name='valid_fnsku_confidence_score'),
        CheckConstraint('cache_hits >= 0', name='cache_hits_non_negative'),
    )