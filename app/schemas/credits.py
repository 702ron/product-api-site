"""
Pydantic schemas for credit management and transactions.
"""
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class TransactionType(str, Enum):
    """Enumeration of transaction types."""
    PURCHASE = "purchase"
    USAGE = "usage"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


class OperationType(str, Enum):
    """Enumeration of operation types."""
    ASIN_QUERY = "asin_query"
    FNSKU_CONVERSION = "fnsku_conversion"
    BULK_ASIN_QUERY = "bulk_asin_query"
    PREMIUM_DATA = "premium_data"


class CreditPackage(str, Enum):
    """Enumeration of available credit packages."""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class CreditBalance(BaseModel):
    """Schema for user credit balance."""
    user_id: uuid.UUID
    current_balance: int
    total_purchased: Optional[int] = None
    total_used: Optional[int] = None
    last_transaction_at: Optional[datetime] = None
    low_balance_warning: bool = False


class CreditTransactionCreate(BaseModel):
    """Schema for creating a credit transaction."""
    amount: int = Field(..., description="Credit amount (positive for addition, negative for usage)")
    transaction_type: TransactionType
    operation: Optional[OperationType] = None
    description: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class CreditTransactionResponse(BaseModel):
    """Schema for credit transaction response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: uuid.UUID
    amount: int
    transaction_type: TransactionType
    operation: Optional[str] = None
    description: Optional[str] = None
    stripe_session_id: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    created_at: datetime


class CreditDeductionRequest(BaseModel):
    """Schema for credit deduction request."""
    operation: OperationType
    cost: Optional[int] = None  # If not provided, will be calculated
    description: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class CreditDeductionResponse(BaseModel):
    """Schema for credit deduction response."""
    success: bool
    credits_deducted: int
    remaining_balance: int
    transaction_id: int
    operation: str


class CreditRefundRequest(BaseModel):
    """Schema for credit refund request."""
    amount: int = Field(..., gt=0, description="Credits to refund")
    reason: str = Field(..., min_length=1, max_length=500)
    original_operation: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class CreditRefundResponse(BaseModel):
    """Schema for credit refund response."""
    success: bool
    credits_refunded: int
    new_balance: int
    transaction_id: int
    reason: str


class CheckoutSessionRequest(BaseModel):
    """Schema for creating Stripe checkout session."""
    package: CreditPackage
    success_url: str = Field(..., description="URL to redirect after successful payment")
    cancel_url: str = Field(..., description="URL to redirect after cancelled payment")


class CheckoutSessionResponse(BaseModel):
    """Schema for checkout session response."""
    checkout_url: str
    session_id: str
    package_info: Dict[str, Any]


class CreditPackageInfo(BaseModel):
    """Schema for credit package information."""
    package: CreditPackage
    credits: int
    price_cents: int
    price_usd: float
    savings_percent: Optional[float] = None
    description: str
    popular: bool = False


class TransactionHistoryRequest(BaseModel):
    """Schema for transaction history request."""
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    transaction_type: Optional[TransactionType] = None
    operation: Optional[OperationType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class TransactionHistoryResponse(BaseModel):
    """Schema for transaction history response."""
    transactions: List[CreditTransactionResponse]
    total_count: int
    has_more: bool
    summary: Dict[str, Any]


class UsageSummaryRequest(BaseModel):
    """Schema for usage summary request."""
    days: int = Field(default=30, ge=1, le=365, description="Number of days to include in summary")


class UsageSummaryResponse(BaseModel):
    """Schema for usage summary response."""
    period_days: int
    start_date: datetime
    end_date: datetime
    total_credits_used: int
    total_credits_purchased: int
    net_credit_change: int
    usage_by_operation: Dict[str, Dict[str, int]]
    daily_usage: Optional[List[Dict[str, Any]]] = None


class CreditAlert(BaseModel):
    """Schema for credit alerts."""
    user_id: uuid.UUID
    alert_type: str  # 'low_balance', 'zero_balance', 'high_usage'
    threshold: int
    current_value: int
    message: str
    created_at: datetime


class BulkOperationRequest(BaseModel):
    """Schema for bulk operation credit calculation."""
    operation: OperationType
    item_count: int = Field(..., ge=1, le=1000)
    parameters: Optional[Dict[str, Any]] = None


class BulkOperationResponse(BaseModel):
    """Schema for bulk operation response."""
    operation: OperationType
    item_count: int
    total_cost: int
    cost_per_item: float
    estimated_duration_seconds: Optional[int] = None
    bulk_discount_applied: bool