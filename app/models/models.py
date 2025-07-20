"""
SQLAlchemy database models for the Amazon Product Intelligence Platform.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, 
    BigInteger, JSON, Text, Boolean, CheckConstraint, Float, Enum
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """User model with credit balance and authentication info."""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
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
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
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
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
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


class PriceMonitor(Base):
    """Price monitoring configuration for products."""
    __tablename__ = "price_monitors"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Product identification
    asin = Column(String(20), nullable=False, index=True)
    marketplace = Column(String(5), nullable=False, default="US")
    
    # Monitoring configuration
    name = Column(String(255), nullable=False)  # User-defined name for the monitor
    target_price = Column(Float, nullable=True)  # Target price to alert on
    threshold_percentage = Column(Float, nullable=True)  # Percentage change threshold
    monitor_frequency_minutes = Column(Integer, nullable=False, default=60)  # Check frequency
    
    # Alert settings
    email_alerts = Column(Boolean, default=True, nullable=False)
    webhook_url = Column(String(500), nullable=True)  # Optional webhook for alerts
    alert_conditions = Column(JSON, nullable=True)  # Custom alert conditions
    
    # Current status
    is_active = Column(Boolean, default=True, nullable=False)
    last_checked_at = Column(DateTime, nullable=True)
    last_price = Column(Float, nullable=True)
    last_alert_sent_at = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="price_monitors")
    price_history = relationship("PriceHistory", back_populates="monitor", cascade="all, delete-orphan")
    price_alerts = relationship("PriceAlert", back_populates="monitor", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('target_price IS NULL OR target_price > 0', name='positive_target_price'),
        CheckConstraint('threshold_percentage IS NULL OR threshold_percentage > 0', name='positive_threshold'),
        CheckConstraint('monitor_frequency_minutes >= 1', name='minimum_frequency'),
        CheckConstraint('consecutive_failures >= 0', name='non_negative_failures'),
    )


class PriceHistory(Base):
    """Historical price data for monitored products."""
    __tablename__ = "price_history"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    monitor_id = Column(String(36), ForeignKey("price_monitors.id", ondelete="CASCADE"), nullable=False)
    
    # Price data
    price = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    availability = Column(String(50), nullable=True)  # In stock, out of stock, etc.
    seller_name = Column(String(255), nullable=True)
    
    # Additional product data
    title = Column(Text, nullable=True)
    product_details = Column(JSON, nullable=True)  # Full product data snapshot
    
    # Change tracking
    price_change = Column(Float, nullable=True)  # Change from previous price
    price_change_percentage = Column(Float, nullable=True)  # Percentage change
    
    # Source metadata
    data_source = Column(String(100), nullable=False, default="amazon_api")
    response_time_ms = Column(Integer, nullable=True)
    
    # Timestamps
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    monitor = relationship("PriceMonitor", back_populates="price_history")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('price > 0', name='positive_price'),
    )


class PriceAlert(Base):
    """Price alert notifications sent to users."""
    __tablename__ = "price_alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    monitor_id = Column(String(36), ForeignKey("price_monitors.id", ondelete="CASCADE"), nullable=False)
    
    # Alert details
    alert_type = Column(
        Enum("price_drop", "target_reached", "threshold_reached", "back_in_stock", "out_of_stock", 
             name="alert_type_enum"), 
        nullable=False
    )
    message = Column(Text, nullable=False)
    
    # Price information
    current_price = Column(Float, nullable=False)
    previous_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    price_change = Column(Float, nullable=True)
    price_change_percentage = Column(Float, nullable=True)
    
    # Notification details
    email_sent = Column(Boolean, default=False, nullable=False)
    webhook_sent = Column(Boolean, default=False, nullable=False)
    email_sent_at = Column(DateTime, nullable=True)
    webhook_sent_at = Column(DateTime, nullable=True)
    
    # Delivery status
    email_delivery_status = Column(String(50), nullable=True)  # sent, delivered, failed, etc.
    webhook_delivery_status = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    monitor = relationship("PriceMonitor", back_populates="price_alerts")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('current_price > 0', name='positive_current_price'),
    )