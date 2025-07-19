"""
Pydantic schemas for Amazon product data and ASIN operations.
"""
import re
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


class Marketplace(str, Enum):
    """Supported Amazon marketplaces."""
    US = "US"
    UK = "UK"
    DE = "DE"
    FR = "FR"
    IT = "IT"
    ES = "ES"
    JP = "JP"
    CA = "CA"
    AU = "AU"
    IN = "IN"


class ProductDataSource(str, Enum):
    """Product data sources."""
    RAINFOREST_API = "rainforest_api"
    AMAZON_PAAPI = "amazon_paapi"
    CACHE = "cache"
    FALLBACK = "fallback"


class ProductAvailability(str, Enum):
    """Product availability status."""
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    DISCONTINUED = "discontinued"
    UNKNOWN = "unknown"


class ProductRequest(BaseModel):
    """Schema for product data request."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    asin: str = Field(..., description="Amazon ASIN (10 characters, starting with B)")
    marketplace: Marketplace = Field(default=Marketplace.US, description="Amazon marketplace")
    include_reviews: bool = Field(default=False, description="Include customer reviews")
    include_offers: bool = Field(default=False, description="Include seller offers")
    include_images: bool = Field(default=True, description="Include product images")
    include_features: bool = Field(default=True, description="Include product features")
    include_description: bool = Field(default=True, description="Include product description")
    use_cache: bool = Field(default=True, description="Use cached data if available")
    
    @field_validator('asin')
    @classmethod
    def validate_asin(cls, v: str) -> str:
        """Validate ASIN format."""
        if not v:
            raise ValueError("ASIN cannot be empty")
        
        # ASIN format: B + 9 alphanumeric characters
        if not re.match(r'^B[0-9A-Z]{9}$', v.upper()):
            raise ValueError(
                "Invalid ASIN format. ASIN must be 10 characters starting with 'B' "
                "followed by 9 alphanumeric characters"
            )
        
        return v.upper()


class ProductPrice(BaseModel):
    """Schema for product pricing information."""
    currency: str = Field(..., description="Currency code (e.g., USD, EUR)")
    amount: Optional[float] = Field(None, description="Price amount")
    formatted: Optional[str] = Field(None, description="Formatted price string")
    
    # Additional pricing details
    list_price: Optional[float] = Field(None, description="Original list price")
    savings: Optional[float] = Field(None, description="Savings amount")
    savings_percent: Optional[float] = Field(None, description="Savings percentage")
    
    # Price history (if available)
    lowest_price_30_days: Optional[float] = None
    highest_price_30_days: Optional[float] = None


class ProductRating(BaseModel):
    """Schema for product rating information."""
    value: Optional[float] = Field(None, ge=0, le=5, description="Rating value (0-5)")
    total_reviews: Optional[int] = Field(None, ge=0, description="Total number of reviews")
    distribution: Optional[Dict[str, int]] = Field(None, description="Rating distribution")


class ProductImage(BaseModel):
    """Schema for product image information."""
    url: str = Field(..., description="Image URL")
    width: Optional[int] = Field(None, description="Image width")
    height: Optional[int] = Field(None, description="Image height")
    variant: Optional[str] = Field(None, description="Image variant (main, thumbnail, etc.)")


class ProductOffer(BaseModel):
    """Schema for product offer/seller information."""
    seller_name: Optional[str] = Field(None, description="Seller name")
    price: Optional[ProductPrice] = Field(None, description="Offer price")
    condition: Optional[str] = Field(None, description="Product condition")
    shipping: Optional[str] = Field(None, description="Shipping information")
    prime_eligible: Optional[bool] = Field(None, description="Prime eligible")


class ProductReview(BaseModel):
    """Schema for customer review."""
    rating: Optional[float] = Field(None, ge=0, le=5, description="Review rating")
    title: Optional[str] = Field(None, description="Review title")
    text: Optional[str] = Field(None, description="Review text")
    author: Optional[str] = Field(None, description="Review author")
    date: Optional[datetime] = Field(None, description="Review date")
    verified_purchase: Optional[bool] = Field(None, description="Verified purchase")
    helpful_votes: Optional[int] = Field(None, description="Helpful votes")


class ProductData(BaseModel):
    """Schema for comprehensive product data."""
    asin: str = Field(..., description="Product ASIN")
    title: Optional[str] = Field(None, description="Product title")
    brand: Optional[str] = Field(None, description="Product brand")
    manufacturer: Optional[str] = Field(None, description="Product manufacturer")
    
    # Pricing
    price: Optional[ProductPrice] = Field(None, description="Product pricing")
    
    # Rating and reviews
    rating: Optional[ProductRating] = Field(None, description="Product rating")
    
    # Images
    images: List[ProductImage] = Field(default_factory=list, description="Product images")
    main_image: Optional[str] = Field(None, description="Main product image URL")
    
    # Product details
    description: Optional[str] = Field(None, description="Product description")
    features: List[str] = Field(default_factory=list, description="Product features")
    category: Optional[str] = Field(None, description="Product category")
    sub_category: Optional[str] = Field(None, description="Product sub-category")
    
    # Availability
    availability: Optional[ProductAvailability] = Field(None, description="Product availability")
    in_stock: Optional[bool] = Field(None, description="In stock status")
    
    # Additional information
    dimensions: Optional[Dict[str, Any]] = Field(None, description="Product dimensions")
    weight: Optional[str] = Field(None, description="Product weight")
    model_number: Optional[str] = Field(None, description="Model number")
    
    # Marketplace and sourcing
    marketplace: Marketplace = Field(..., description="Amazon marketplace")
    data_source: ProductDataSource = Field(..., description="Data source")
    
    # Offers and sellers (if requested)
    offers: List[ProductOffer] = Field(default_factory=list, description="Product offers")
    
    # Reviews (if requested)
    reviews: List[ProductReview] = Field(default_factory=list, description="Customer reviews")
    
    # Metadata
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    cache_expires_at: Optional[datetime] = Field(None, description="Cache expiration")


class ProductResponse(BaseModel):
    """Schema for product API response."""
    status: str = Field(..., description="Response status")
    credits_used: int = Field(..., description="Credits consumed")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    
    # Product data (if successful)
    data: Optional[ProductData] = Field(None, description="Product data")
    
    # Error information (if failed)
    error: Optional[str] = Field(None, description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    
    # Cache information
    from_cache: bool = Field(default=False, description="Response served from cache")
    cache_age_seconds: Optional[int] = Field(None, description="Cache age in seconds")


class BulkProductRequest(BaseModel):
    """Schema for bulk product data request."""
    asins: List[str] = Field(..., min_length=1, max_length=100, description="List of ASINs")
    marketplace: Marketplace = Field(default=Marketplace.US, description="Amazon marketplace")
    include_reviews: bool = Field(default=False, description="Include customer reviews")
    include_offers: bool = Field(default=False, description="Include seller offers")
    include_images: bool = Field(default=True, description="Include product images")
    use_cache: bool = Field(default=True, description="Use cached data if available")
    
    @field_validator('asins')
    @classmethod
    def validate_asins(cls, v: List[str]) -> List[str]:
        """Validate all ASINs in the list."""
        validated_asins = []
        for asin in v:
            if not asin:
                continue
            if not re.match(r'^B[0-9A-Z]{9}$', asin.upper()):
                raise ValueError(f"Invalid ASIN format: {asin}")
            validated_asins.append(asin.upper())
        
        if not validated_asins:
            raise ValueError("At least one valid ASIN is required")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_asins = []
        for asin in validated_asins:
            if asin not in seen:
                seen.add(asin)
                unique_asins.append(asin)
        
        return unique_asins


class BulkProductResponse(BaseModel):
    """Schema for bulk product API response."""
    status: str = Field(..., description="Response status")
    total_requested: int = Field(..., description="Total ASINs requested")
    total_processed: int = Field(..., description="Total ASINs processed")
    total_credits_used: int = Field(..., description="Total credits consumed")
    processing_time_ms: Optional[int] = Field(None, description="Total processing time")
    
    # Results
    products: List[ProductData] = Field(default_factory=list, description="Product data")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Processing errors")
    
    # Cache statistics
    cache_hits: int = Field(default=0, description="Number of cache hits")
    cache_misses: int = Field(default=0, description="Number of cache misses")


class ProductSearchRequest(BaseModel):
    """Schema for product search request (future feature)."""
    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    marketplace: Marketplace = Field(default=Marketplace.US, description="Amazon marketplace")
    category: Optional[str] = Field(None, description="Product category filter")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price filter")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter")
    min_rating: Optional[float] = Field(None, ge=0, le=5, description="Minimum rating filter")
    sort_by: Optional[str] = Field(default="relevance", description="Sort criteria")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Results per page")


class ProductValidationResponse(BaseModel):
    """Schema for ASIN validation response."""
    asin: str = Field(..., description="Validated ASIN")
    valid: bool = Field(..., description="Validation result")
    formatted_asin: Optional[str] = Field(None, description="Correctly formatted ASIN")
    errors: List[str] = Field(default_factory=list, description="Validation errors")


class ProductCacheStats(BaseModel):
    """Schema for product cache statistics."""
    total_cached_products: int = Field(..., description="Total products in cache")
    cache_hit_rate: float = Field(..., description="Cache hit rate percentage")
    average_cache_age_hours: float = Field(..., description="Average cache age in hours")
    expired_entries: int = Field(..., description="Number of expired entries")
    marketplaces: Dict[str, int] = Field(..., description="Products per marketplace")