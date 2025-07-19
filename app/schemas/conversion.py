"""
Pydantic schemas for FNSKU to ASIN conversion functionality.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class ConversionConfidence(str, Enum):
    """Confidence levels for FNSKU to ASIN conversion."""
    NONE = "none"           # 0.0 - 0.2
    LOW = "low"             # 0.2 - 0.4
    MEDIUM = "medium"       # 0.4 - 0.7
    HIGH = "high"           # 0.7 - 0.9
    VERY_HIGH = "very_high" # 0.9 - 1.0

    def __new__(cls, value):
        obj = str.__new__(cls, value)
        obj._value_ = value
        return obj

    @classmethod
    def from_score(cls, score: float) -> "ConversionConfidence":
        """Convert numeric confidence score to enum."""
        if score >= 0.9:
            return cls.VERY_HIGH
        elif score >= 0.7:
            return cls.HIGH
        elif score >= 0.4:
            return cls.MEDIUM
        elif score >= 0.2:
            return cls.LOW
        else:
            return cls.NONE

    @property
    def numeric_value(self) -> float:
        """Get the numeric confidence value."""
        mapping = {
            "none": 0.0,
            "low": 0.3,
            "medium": 0.55,
            "high": 0.8,
            "very_high": 0.95
        }
        return mapping.get(self.value, 0.0)


class ConversionMethod(str, Enum):
    """Methods used for FNSKU to ASIN conversion."""
    DIRECT_API = "direct_api"           # Direct Amazon API lookup
    PATTERN_MATCHING = "pattern_matching" # Pattern matching and heuristics
    DATABASE_LOOKUP = "database_lookup"  # Internal database matching
    MANUAL_MAPPING = "manual_mapping"    # Pre-configured mappings
    MACHINE_LEARNING = "machine_learning" # ML-based conversion
    FAILED = "failed"                   # All methods failed


class FnskuValidationResult(BaseModel):
    """Result of FNSKU format validation."""
    fnsku: str = Field(..., description="Original FNSKU input")
    formatted_fnsku: Optional[str] = Field(None, description="Properly formatted FNSKU")
    valid: bool = Field(..., description="Whether the FNSKU format is valid")
    errors: List[str] = Field(default_factory=list, description="Validation error messages")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions to fix invalid FNSKU")


class ConversionResult(BaseModel):
    """Result of FNSKU to ASIN conversion."""
    fnsku: str = Field(..., description="Original FNSKU")
    asin: Optional[str] = Field(None, description="Converted ASIN (null if conversion failed)")
    confidence: ConversionConfidence = Field(..., description="Confidence level of the conversion")
    method: ConversionMethod = Field(..., description="Method used for conversion")
    success: bool = Field(..., description="Whether conversion was successful")
    cached: bool = Field(False, description="Whether result came from cache")
    cache_age_hours: float = Field(0.0, description="Age of cached result in hours")
    conversion_time_ms: int = Field(..., description="Time taken for conversion in milliseconds")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional conversion details")
    error_message: Optional[str] = Field(None, description="Error message if conversion failed")
    
    @validator('confidence', pre=True)
    def convert_confidence(cls, v):
        """Convert numeric confidence to enum."""
        if isinstance(v, (int, float)):
            return ConversionConfidence.from_score(float(v))
        return v


class ConversionRequest(BaseModel):
    """Request for FNSKU to ASIN conversion."""
    fnsku: str = Field(..., description="FNSKU to convert", example="X001ABC123")
    marketplace: str = Field("US", description="Amazon marketplace", example="US")
    use_cache: bool = Field(True, description="Use cached results if available")
    verify_asin: bool = Field(True, description="Verify the resulting ASIN exists")


class ConversionResponse(BaseModel):
    """Response for FNSKU to ASIN conversion."""
    status: str = Field(..., description="Response status", example="success")
    conversion: ConversionResult = Field(..., description="Conversion result")
    credits_used: int = Field(..., description="Credits consumed for the conversion")
    response_time_ms: int = Field(..., description="Total response time in milliseconds")


class BulkConversionRequest(BaseModel):
    """Request for bulk FNSKU to ASIN conversion."""
    fnskus: List[str] = Field(..., description="List of FNSKUs to convert", min_items=1, max_items=100)
    marketplace: str = Field("US", description="Amazon marketplace", example="US")
    use_cache: bool = Field(True, description="Use cached results if available")
    
    @validator('fnskus')
    def validate_fnskus_limit(cls, v):
        """Ensure reasonable limits on bulk requests."""
        if len(v) > 100:
            raise ValueError("Maximum 100 FNSKUs per bulk request")
        if len(set(v)) != len(v):
            raise ValueError("Duplicate FNSKUs not allowed in bulk request")
        return v


class BulkConversionResponse(BaseModel):
    """Response for bulk FNSKU to ASIN conversion."""
    status: str = Field(..., description="Overall status", example="success")
    total_requested: int = Field(..., description="Total FNSKUs requested")
    total_successful: int = Field(..., description="Number of successful conversions")
    total_failed: int = Field(..., description="Number of failed conversions")
    total_credits_used: int = Field(..., description="Total credits consumed")
    processing_time_ms: int = Field(..., description="Total processing time in milliseconds")
    conversions: List[ConversionResult] = Field(..., description="Individual conversion results")
    cache_hits: int = Field(0, description="Number of results from cache")
    cache_misses: int = Field(0, description="Number of results requiring new conversion")


class ConversionStats(BaseModel):
    """Statistics for FNSKU conversion service."""
    total_conversions: int = Field(..., description="Total conversion attempts")
    successful_conversions: int = Field(..., description="Number of successful conversions")
    success_rate: float = Field(..., description="Success rate as percentage")
    average_confidence: float = Field(..., description="Average confidence score")
    method_distribution: Dict[str, int] = Field(..., description="Distribution of conversion methods used")
    cache_entries: int = Field(..., description="Number of cached conversion results")


class ConversionBatchStatus(BaseModel):
    """Status of a batch conversion job."""
    batch_id: str = Field(..., description="Unique batch identifier")
    status: str = Field(..., description="Batch status", example="processing")
    total_items: int = Field(..., description="Total items in batch")
    processed_items: int = Field(..., description="Items processed so far")
    successful_items: int = Field(..., description="Successfully converted items")
    failed_items: int = Field(..., description="Failed conversion items")
    estimated_completion_time: Optional[datetime] = Field(None, description="Estimated completion time")
    created_at: datetime = Field(..., description="Batch creation time")
    started_at: Optional[datetime] = Field(None, description="Processing start time")
    completed_at: Optional[datetime] = Field(None, description="Processing completion time")


class FnskuSuggestionRequest(BaseModel):
    """Request for FNSKU format suggestions."""
    input_value: str = Field(..., description="Invalid FNSKU input", example="x001abc123")


class FnskuSuggestionResponse(BaseModel):
    """Response with FNSKU format suggestions."""
    original_input: str = Field(..., description="Original input value")
    suggestions: List[str] = Field(..., description="Suggested corrections")
    auto_corrected: Optional[str] = Field(None, description="Automatically corrected FNSKU if possible")
    validation_result: FnskuValidationResult = Field(..., description="Validation details")


class ConversionCacheInfo(BaseModel):
    """Information about conversion cache."""
    fnsku: str = Field(..., description="FNSKU")
    asin: Optional[str] = Field(None, description="Cached ASIN")
    confidence_score: float = Field(..., description="Cached confidence score")
    conversion_method: str = Field(..., description="Method used for original conversion")
    created_at: datetime = Field(..., description="Cache entry creation time")
    expires_at: datetime = Field(..., description="Cache expiration time")
    is_stale: bool = Field(..., description="Whether cache entry is stale")
    cache_hits: int = Field(0, description="Number of times this cache entry was used")


class ConversionPerformanceMetrics(BaseModel):
    """Performance metrics for conversion service."""
    average_conversion_time_ms: float = Field(..., description="Average conversion time")
    cache_hit_rate: float = Field(..., description="Cache hit rate as percentage")
    method_performance: Dict[str, float] = Field(..., description="Average time per conversion method")
    success_rates_by_method: Dict[str, float] = Field(..., description="Success rate per conversion method")
    recent_conversions: int = Field(..., description="Conversions in last 24 hours")
    peak_conversion_time: float = Field(..., description="Peak conversion time in last hour")


class ConversionHealthCheck(BaseModel):
    """Health check for conversion service."""
    service_status: str = Field(..., description="Service health status", example="healthy")
    cache_status: str = Field(..., description="Cache system status")
    api_status: str = Field(..., description="External API status")
    database_status: str = Field(..., description="Database connection status")
    recent_error_rate: float = Field(..., description="Error rate in last hour")
    average_response_time_ms: float = Field(..., description="Average response time")
    uptime_seconds: int = Field(..., description="Service uptime in seconds")
    last_maintenance: Optional[datetime] = Field(None, description="Last maintenance time")