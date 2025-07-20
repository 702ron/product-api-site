"""
Pydantic schemas for price monitoring endpoints.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator

from app.core.queue import JobPriority


class PriceMonitorCreate(BaseModel):
    """Schema for creating a price monitor."""
    asin: str = Field(min_length=10, max_length=20, description="Amazon ASIN")
    marketplace: str = Field(default="US", description="Amazon marketplace")
    name: str = Field(min_length=1, max_length=255, description="Monitor name")
    target_price: Optional[float] = Field(None, gt=0, description="Target price to alert on")
    threshold_percentage: Optional[float] = Field(None, gt=0, le=100, description="Price change threshold percentage")
    monitor_frequency_minutes: int = Field(default=60, ge=1, le=1440, description="Check frequency in minutes")
    email_alerts: bool = Field(default=True, description="Enable email alerts")
    webhook_url: Optional[str] = Field(None, max_length=500, description="Webhook URL for alerts")
    alert_conditions: Optional[Dict[str, Any]] = Field(None, description="Custom alert conditions")
    
    @validator('asin')
    def validate_asin(cls, v):
        """Validate ASIN format."""
        if not v.isalnum():
            raise ValueError('ASIN must be alphanumeric')
        return v.upper()
    
    @validator('marketplace')
    def validate_marketplace(cls, v):
        """Validate marketplace."""
        valid_marketplaces = ['US', 'UK', 'DE', 'FR', 'IT', 'ES', 'CA', 'JP']
        if v.upper() not in valid_marketplaces:
            raise ValueError(f'Marketplace must be one of: {", ".join(valid_marketplaces)}')
        return v.upper()
    
    class Config:
        schema_extra = {
            "example": {
                "asin": "B08N5WRWNW",
                "marketplace": "US",
                "name": "Echo Dot (4th Gen)",
                "target_price": 29.99,
                "threshold_percentage": 10.0,
                "monitor_frequency_minutes": 60,
                "email_alerts": True,
                "webhook_url": "https://example.com/webhook",
                "alert_conditions": {}
            }
        }


class PriceMonitorUpdate(BaseModel):
    """Schema for updating a price monitor."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    target_price: Optional[float] = Field(None, gt=0)
    threshold_percentage: Optional[float] = Field(None, gt=0, le=100)
    monitor_frequency_minutes: Optional[int] = Field(None, ge=1, le=1440)
    email_alerts: Optional[bool] = None
    webhook_url: Optional[str] = Field(None, max_length=500)
    alert_conditions: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class PriceMonitorResponse(BaseModel):
    """Schema for price monitor response."""
    id: str
    user_id: str
    asin: str
    marketplace: str
    name: str
    target_price: Optional[float]
    threshold_percentage: Optional[float]
    monitor_frequency_minutes: int
    email_alerts: bool
    webhook_url: Optional[str]
    alert_conditions: Optional[Dict[str, Any]]
    is_active: bool
    last_checked_at: Optional[datetime]
    last_price: Optional[float]
    last_alert_sent_at: Optional[datetime]
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PriceHistoryResponse(BaseModel):
    """Schema for price history response."""
    id: int
    monitor_id: str
    price: float
    currency: str
    availability: Optional[str]
    seller_name: Optional[str]
    title: Optional[str]
    price_change: Optional[float]
    price_change_percentage: Optional[float]
    data_source: str
    response_time_ms: Optional[int]
    recorded_at: datetime
    
    class Config:
        from_attributes = True


class PriceAlertResponse(BaseModel):
    """Schema for price alert response."""
    id: str
    monitor_id: str
    alert_type: str
    message: str
    current_price: float
    previous_price: Optional[float]
    target_price: Optional[float]
    price_change: Optional[float]
    price_change_percentage: Optional[float]
    email_sent: bool
    webhook_sent: bool
    email_sent_at: Optional[datetime]
    webhook_sent_at: Optional[datetime]
    email_delivery_status: Optional[str]
    webhook_delivery_status: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class PriceMonitorListResponse(BaseModel):
    """Schema for listing price monitors."""
    monitors: List[PriceMonitorResponse]
    total: int


class PriceHistoryListResponse(BaseModel):
    """Schema for listing price history."""
    history: List[PriceHistoryResponse]
    total: int
    monitor: PriceMonitorResponse


class PriceAlertListResponse(BaseModel):
    """Schema for listing price alerts."""
    alerts: List[PriceAlertResponse]
    total: int


class MonitorStatsResponse(BaseModel):
    """Schema for monitor statistics."""
    total_monitors: int
    active_monitors: int
    total_checks_today: int
    total_alerts_today: int
    avg_price_change_percentage: float
    top_monitored_asins: List[Dict[str, Any]]


class BulkMonitorRequest(BaseModel):
    """Schema for bulk monitor operations."""
    monitor_ids: List[str] = Field(min_items=1, max_items=100)
    action: str = Field(description="Action to perform: activate, deactivate, delete")
    
    @validator('action')
    def validate_action(cls, v):
        """Validate action."""
        if v not in ['activate', 'deactivate', 'delete']:
            raise ValueError('Action must be one of: activate, deactivate, delete')
        return v


class BulkMonitorResponse(BaseModel):
    """Schema for bulk monitor operation response."""
    success_count: int
    failure_count: int
    results: List[Dict[str, Any]]


class MonitorTestRequest(BaseModel):
    """Schema for testing a monitor."""
    asin: str = Field(min_length=10, max_length=20)
    marketplace: str = Field(default="US")
    
    @validator('asin')
    def validate_asin(cls, v):
        """Validate ASIN format."""
        if not v.isalnum():
            raise ValueError('ASIN must be alphanumeric')
        return v.upper()


class MonitorTestResponse(BaseModel):
    """Schema for monitor test response."""
    asin: str
    marketplace: str
    current_price: Optional[float]
    availability: Optional[str]
    title: Optional[str]
    response_time_ms: int
    success: bool
    error_message: Optional[str]