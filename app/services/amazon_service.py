"""
Amazon product data service with external API integration, caching, and rate limiting.
"""
import json
import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import httpx
# import aioredis  # Temporarily disabled for testing
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.models.models import ProductCache
from app.schemas.products import (
    ProductData, ProductPrice, ProductRating, ProductImage,
    ProductAvailability, ProductDataSource, Marketplace
)
from app.core.exceptions import ExternalServiceError, ProductNotFoundError, RateLimitError

logger = logging.getLogger(__name__)


# Re-export for backward compatibility
class ExternalAPIError(ExternalServiceError):
    """Exception for external API errors."""
    pass


class RateLimitExceededError(RateLimitError):
    """Exception when rate limit is exceeded."""
    pass


class AmazonService:
    """Service for Amazon product data retrieval with caching and rate limiting."""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Amazon-Product-Intelligence-Platform/1.0"
            }
        )
        # self.redis_client: Optional[aioredis.Redis] = None  # Temporarily disabled
        self.rate_limit_calls = {}  # In-memory rate limiting
        
        # API configuration
        self.api_key = settings.amazon_api_key
        self.api_url = settings.amazon_api_url
        
        # Rate limiting configuration
        self.max_calls_per_minute = 60
        self.max_calls_per_second = 2
        
    # async def _get_redis_client(self) -> aioredis.Redis:
    #     """Get Redis client for caching."""
    #     if self.redis_client is None:
    #         self.redis_client = aioredis.from_url(settings.redis_url)
    #     return self.redis_client
    
    async def _check_rate_limit(self, marketplace: str) -> bool:
        """
        Check and enforce rate limiting.
        
        Args:
            marketplace: Amazon marketplace
            
        Returns:
            True if request is allowed
            
        Raises:
            RateLimitExceededError: If rate limit exceeded
        """
        current_time = time.time()
        key = f"rate_limit:{marketplace}"
        
        # Simple in-memory rate limiting
        if key not in self.rate_limit_calls:
            self.rate_limit_calls[key] = []
        
        # Clean old calls (older than 1 minute)
        self.rate_limit_calls[key] = [
            call_time for call_time in self.rate_limit_calls[key]
            if current_time - call_time < 60
        ]
        
        # Check rate limit
        if len(self.rate_limit_calls[key]) >= self.max_calls_per_minute:
            raise RateLimitExceededError(f"Rate limit exceeded for marketplace {marketplace}")
        
        # Add current call
        self.rate_limit_calls[key].append(current_time)
        
        # Add small delay to respect per-second limit
        if len(self.rate_limit_calls[key]) > 1:
            last_call = self.rate_limit_calls[key][-2]
            time_since_last = current_time - last_call
            if time_since_last < (1.0 / self.max_calls_per_second):
                await asyncio.sleep((1.0 / self.max_calls_per_second) - time_since_last)
        
        return True
    
    async def _get_cached_product(
        self,
        db: AsyncSession,
        asin: str,
        marketplace: str
    ) -> Optional[ProductData]:
        """
        Get product data from cache.
        
        Args:
            db: Database session
            asin: Product ASIN
            marketplace: Amazon marketplace
            
        Returns:
            Cached product data or None
        """
        try:
            # Check database cache
            result = await db.execute(
                select(ProductCache).where(
                    and_(
                        ProductCache.asin == asin,
                        ProductCache.marketplace == marketplace,
                        ProductCache.expires_at > datetime.utcnow()
                    )
                )
            )
            cache_entry = result.scalar_one_or_none()
            
            if cache_entry and not cache_entry.is_stale:
                logger.info(f"Cache hit for {asin} in {marketplace}")
                product_data = ProductData(
                    **cache_entry.product_data,
                    data_source=ProductDataSource.CACHE,
                    last_updated=cache_entry.last_updated,
                    cache_expires_at=cache_entry.expires_at
                )
                return product_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached product {asin}: {str(e)}")
            return None
    
    async def _cache_product(
        self,
        db: AsyncSession,
        asin: str,
        marketplace: str,
        product_data: ProductData,
        ttl_hours: int = 24
    ) -> bool:
        """
        Cache product data.
        
        Args:
            db: Database session
            asin: Product ASIN
            marketplace: Amazon marketplace
            product_data: Product data to cache
            ttl_hours: Cache TTL in hours
            
        Returns:
            True if cached successfully
        """
        try:
            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
            cache_key = f"product:{asin}:{marketplace}"
            
            # Prepare data for caching (exclude cache metadata)
            cache_data = product_data.model_dump(exclude={
                'data_source', 'last_updated', 'cache_expires_at'
            })
            
            # Update or create cache entry
            result = await db.execute(
                select(ProductCache).where(
                    and_(
                        ProductCache.asin == asin,
                        ProductCache.marketplace == marketplace
                    )
                )
            )
            cache_entry = result.scalar_one_or_none()
            
            if cache_entry:
                cache_entry.product_data = cache_data
                cache_entry.last_updated = datetime.utcnow()
                cache_entry.expires_at = expires_at
                cache_entry.is_stale = False
                cache_entry.data_source = product_data.data_source.value
            else:
                cache_entry = ProductCache(
                    asin=asin,
                    marketplace=marketplace,
                    product_data=cache_data,
                    data_source=product_data.data_source.value,
                    cache_key=cache_key,
                    last_updated=datetime.utcnow(),
                    expires_at=expires_at,
                    is_stale=False
                )
                db.add(cache_entry)
            
            await db.commit()
            logger.info(f"Cached product {asin} for {marketplace}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching product {asin}: {str(e)}")
            await db.rollback()
            return False
    
    async def _call_rainforest_api(
        self,
        asin: str,
        marketplace: str,
        include_reviews: bool = False
    ) -> Dict[str, Any]:
        """
        Call Rainforest API for product data.
        
        Args:
            asin: Product ASIN
            marketplace: Amazon marketplace
            include_reviews: Include review data
            
        Returns:
            API response data
            
        Raises:
            ExternalAPIError: If API call fails
        """
        params = {
            "api_key": self.api_key,
            "type": "product",
            "amazon_domain": f"amazon.{marketplace.lower()}" if marketplace != "US" else "amazon.com",
            "asin": asin
        }
        
        if include_reviews:
            params["reviews"] = "true"
        
        try:
            response = await self.http_client.get(self.api_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if "product" not in data:
                raise ProductNotFoundError(f"Product {asin} not found in {marketplace}")
            
            return data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ProductNotFoundError(f"Product {asin} not found")
            elif e.response.status_code == 429:
                raise RateLimitExceededError("External API rate limit exceeded")
            else:
                raise ExternalAPIError(f"API error: {e.response.status_code}")
        except httpx.RequestError as e:
            raise ExternalAPIError(f"Request error: {str(e)}")
    
    def _parse_rainforest_data(self, data: Dict[str, Any], marketplace: str) -> ProductData:
        """
        Parse Rainforest API response into ProductData.
        
        Args:
            data: Rainforest API response
            marketplace: Amazon marketplace
            
        Returns:
            Parsed product data
        """
        product = data.get("product", {})
        
        # Parse price information
        price_data = None
        if "buybox_winner" in product:
            buybox = product["buybox_winner"]
            price_data = ProductPrice(
                currency=buybox.get("price", {}).get("currency", "USD"),
                amount=buybox.get("price", {}).get("value"),
                formatted=buybox.get("price", {}).get("raw")
            )
        
        # Parse rating information
        rating_data = None
        if "rating" in product:
            rating_data = ProductRating(
                value=product["rating"],
                total_reviews=product.get("ratings_total")
            )
        
        # Parse images
        images = []
        if "images" in product:
            for i, img in enumerate(product["images"]):
                images.append(ProductImage(
                    url=img.get("link", ""),
                    variant="main" if i == 0 else "additional"
                ))
        
        # Parse features
        features = []
        if "feature_bullets" in product:
            features = [bullet.get("text", "") for bullet in product["feature_bullets"]]
        
        # Determine availability
        availability = ProductAvailability.UNKNOWN
        if "buybox_winner" in product:
            availability = ProductAvailability.IN_STOCK
        elif product.get("title") and "unavailable" not in product.get("title", "").lower():
            availability = ProductAvailability.IN_STOCK
        
        return ProductData(
            asin=product.get("asin", ""),
            title=product.get("title"),
            brand=product.get("brand"),
            price=price_data,
            rating=rating_data,
            images=images,
            main_image=images[0].url if images else None,
            description=product.get("description"),
            features=features,
            category=product.get("category", {}).get("name") if "category" in product else None,
            availability=availability,
            in_stock=availability == ProductAvailability.IN_STOCK,
            marketplace=Marketplace(marketplace),
            data_source=ProductDataSource.RAINFOREST_API,
            last_updated=datetime.utcnow()
        )
    
    async def get_product_data(
        self,
        db: AsyncSession,
        asin: str,
        marketplace: str = "US",
        include_reviews: bool = False,
        use_cache: bool = True
    ) -> ProductData:
        """
        Get comprehensive product data for an ASIN.
        
        Args:
            db: Database session
            asin: Product ASIN
            marketplace: Amazon marketplace
            include_reviews: Include customer reviews
            use_cache: Use cached data if available
            
        Returns:
            Product data
            
        Raises:
            ProductNotFoundError: If product not found
            RateLimitExceededError: If rate limit exceeded
            ExternalAPIError: If external API fails
        """
        start_time = time.time()
        
        try:
            # Check cache first
            if use_cache:
                cached_data = await self._get_cached_product(db, asin, marketplace)
                if cached_data:
                    return cached_data
            
            # Check rate limit
            await self._check_rate_limit(marketplace)
            
            # Call external API
            logger.info(f"Fetching product data for {asin} from {marketplace}")
            api_data = await self._call_rainforest_api(asin, marketplace, include_reviews)
            
            # Parse response
            product_data = self._parse_rainforest_data(api_data, marketplace)
            
            # Cache the result
            if use_cache:
                await self._cache_product(db, asin, marketplace, product_data)
            
            # Log performance
            response_time = (time.time() - start_time) * 1000
            logger.info(f"Retrieved product {asin} in {response_time:.2f}ms")
            
            return product_data
            
        except (ProductNotFoundError, RateLimitExceededError, ExternalAPIError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting product {asin}: {str(e)}")
            raise ExternalAPIError(f"Unexpected error: {str(e)}")
    
    async def get_bulk_product_data(
        self,
        db: AsyncSession,
        asins: List[str],
        marketplace: str = "US",
        use_cache: bool = True
    ) -> List[ProductData]:
        """
        Get product data for multiple ASINs with bulk optimization.
        
        Args:
            db: Database session
            asins: List of ASINs
            marketplace: Amazon marketplace
            use_cache: Use cached data if available
            
        Returns:
            List of product data
        """
        results = []
        
        # Process ASINs with some delay to respect rate limits
        for asin in asins:
            try:
                product_data = await self.get_product_data(
                    db, asin, marketplace, use_cache=use_cache
                )
                results.append(product_data)
                
                # Small delay between requests for bulk operations
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error getting product {asin}: {str(e)}")
                # Continue with next ASIN
                continue
        
        return results
    
    async def validate_asin(self, asin: str) -> bool:
        """
        Validate ASIN format.
        
        Args:
            asin: ASIN to validate
            
        Returns:
            True if valid ASIN format
        """
        import re
        return bool(re.match(r'^B[0-9A-Z]{9}$', asin.upper()))
    
    async def cleanup_expired_cache(self, db: AsyncSession) -> int:
        """
        Clean up expired cache entries.
        
        Args:
            db: Database session
            
        Returns:
            Number of entries removed
        """
        try:
            from sqlalchemy import delete
            
            result = await db.execute(
                delete(ProductCache).where(
                    ProductCache.expires_at < datetime.utcnow()
                )
            )
            await db.commit()
            
            removed_count = result.rowcount
            logger.info(f"Cleaned up {removed_count} expired cache entries")
            return removed_count
            
        except Exception as e:
            logger.error(f"Error cleaning up cache: {str(e)}")
            await db.rollback()
            return 0
    
    async def close(self):
        """Close HTTP client and Redis connection."""
        await self.http_client.aclose()
        # if self.redis_client:
        #     await self.redis_client.close()


# Global Amazon service instance
amazon_service = AmazonService()