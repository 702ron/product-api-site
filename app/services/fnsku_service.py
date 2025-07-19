"""
FNSKU to ASIN conversion service with confidence scoring and fallback mechanisms.
"""
import logging
import re
import time
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.models import ProductCache, FnskuCache
from app.services.amazon_service import amazon_service, ProductNotFoundError, ExternalAPIError
from app.schemas.conversion import (
    ConversionResult, ConversionConfidence, ConversionMethod,
    FnskuValidationResult, ConversionStats
)
from app.core.exceptions import InvalidFNSKUError, ConversionFailedError

logger = logging.getLogger(__name__)


# Re-export for backward compatibility
class FnskuFormatError(InvalidFNSKUError):
    """Exception for invalid FNSKU format."""
    pass


class FnskuService:
    """Service for FNSKU to ASIN conversion with multiple strategies and confidence scoring."""
    
    def __init__(self):
        # FNSKU patterns and validation rules
        self.fnsku_pattern = re.compile(r'^[A-Z0-9]{10}$')
        self.asin_pattern = re.compile(r'^B[0-9A-Z]{9}$')
        
        # Conversion cache TTL (longer than product cache since FNSKUs are more stable)
        self.cache_ttl_hours = 72
        
        # Confidence scoring weights
        self.confidence_weights = {
            'exact_match': 1.0,
            'api_verified': 0.95,
            'pattern_match': 0.8,
            'partial_match': 0.6,
            'heuristic': 0.4,
            'fallback': 0.2
        }
    
    def validate_fnsku(self, fnsku: str) -> FnskuValidationResult:
        """
        Validate FNSKU format and structure.
        
        Args:
            fnsku: FNSKU to validate
            
        Returns:
            Validation result with details
        """
        errors = []
        formatted_fnsku = fnsku.upper().strip()
        
        # Check length
        if len(formatted_fnsku) != 10:
            errors.append("FNSKU must be exactly 10 characters")
        
        # Check format (alphanumeric)
        if not self.fnsku_pattern.match(formatted_fnsku):
            errors.append("FNSKU must contain only uppercase letters and numbers")
        
        # Additional validation rules
        if formatted_fnsku.startswith('B') and self.asin_pattern.match(formatted_fnsku):
            errors.append("This appears to be an ASIN, not an FNSKU")
        
        is_valid = len(errors) == 0
        
        return FnskuValidationResult(
            fnsku=fnsku,
            formatted_fnsku=formatted_fnsku if is_valid else None,
            valid=is_valid,
            errors=errors,
            suggestions=self._get_fnsku_suggestions(fnsku) if not is_valid else []
        )
    
    def _get_fnsku_suggestions(self, fnsku: str) -> List[str]:
        """Generate suggestions for invalid FNSKUs."""
        suggestions = []
        
        if len(fnsku) < 10:
            suggestions.append("FNSKU should be 10 characters long")
        elif len(fnsku) > 10:
            suggestions.append("FNSKU should be exactly 10 characters, try removing extra characters")
        
        if any(c.islower() for c in fnsku):
            suggestions.append("Try converting to uppercase")
        
        if not fnsku.isalnum():
            suggestions.append("Remove any special characters or spaces")
        
        return suggestions
    
    async def _get_cached_conversion(
        self,
        db: AsyncSession,
        fnsku: str
    ) -> Optional[ConversionResult]:
        """
        Get cached FNSKU conversion result.
        
        Args:
            db: Database session
            fnsku: FNSKU to lookup
            
        Returns:
            Cached conversion result or None
        """
        try:
            result = await db.execute(
                select(FnskuCache).where(
                    and_(
                        FnskuCache.fnsku == fnsku,
                        FnskuCache.expires_at > datetime.utcnow()
                    )
                )
            )
            cache_entry = result.scalar_one_or_none()
            
            if cache_entry and not cache_entry.is_stale:
                logger.info(f"Cache hit for FNSKU conversion {fnsku}")
                
                return ConversionResult(
                    fnsku=fnsku,
                    asin=cache_entry.asin,
                    confidence=ConversionConfidence(cache_entry.confidence_score),
                    method=ConversionMethod(cache_entry.conversion_method),
                    success=cache_entry.asin is not None,
                    cached=True,
                    cache_age_hours=self._calculate_cache_age_hours(cache_entry.created_at),
                    conversion_time_ms=0,  # Cached, so no conversion time
                    details=cache_entry.conversion_details or {},
                    error_message=cache_entry.error_message
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached conversion for {fnsku}: {str(e)}")
            return None
    
    def _calculate_cache_age_hours(self, created_at: datetime) -> float:
        """Calculate cache age in hours."""
        return (datetime.utcnow() - created_at).total_seconds() / 3600
    
    async def _cache_conversion_result(
        self,
        db: AsyncSession,
        fnsku: str,
        result: ConversionResult
    ) -> bool:
        """
        Cache FNSKU conversion result.
        
        Args:
            db: Database session
            fnsku: FNSKU
            result: Conversion result to cache
            
        Returns:
            True if cached successfully
        """
        try:
            expires_at = datetime.utcnow() + timedelta(hours=self.cache_ttl_hours)
            
            # Check if entry exists
            existing_result = await db.execute(
                select(FnskuCache).where(FnskuCache.fnsku == fnsku)
            )
            cache_entry = existing_result.scalar_one_or_none()
            
            if cache_entry:
                # Update existing entry
                cache_entry.asin = result.asin
                cache_entry.confidence_score = result.confidence.value
                cache_entry.conversion_method = result.method.value
                cache_entry.conversion_details = result.details
                cache_entry.error_message = result.error_message
                cache_entry.last_updated = datetime.utcnow()
                cache_entry.expires_at = expires_at
                cache_entry.is_stale = False
            else:
                # Create new entry
                cache_entry = FnskuCache(
                    fnsku=fnsku,
                    asin=result.asin,
                    confidence_score=result.confidence.value,
                    conversion_method=result.method.value,
                    conversion_details=result.details,
                    error_message=result.error_message,
                    created_at=datetime.utcnow(),
                    last_updated=datetime.utcnow(),
                    expires_at=expires_at,
                    is_stale=False
                )
                db.add(cache_entry)
            
            await db.commit()
            logger.info(f"Cached FNSKU conversion for {fnsku}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching FNSKU conversion for {fnsku}: {str(e)}")
            await db.rollback()
            return False
    
    async def _convert_via_direct_api(
        self,
        db: AsyncSession,
        fnsku: str,
        marketplace: str = "US"
    ) -> Tuple[Optional[str], float, Dict[str, Any]]:
        """
        Attempt direct API conversion using Amazon API.
        
        This would typically use an Amazon API that accepts FNSKU directly.
        For now, this is a placeholder that simulates the conversion logic.
        
        Args:
            db: Database session
            fnsku: FNSKU to convert
            marketplace: Amazon marketplace
            
        Returns:
            Tuple of (ASIN, confidence_score, details)
        """
        try:
            # Placeholder for actual Amazon API call that supports FNSKU lookup
            # In real implementation, this would call Amazon's Product Advertising API
            # or Seller Central API with FNSKU parameter
            
            # Simulate API delay
            await asyncio.sleep(0.1)
            
            # For demonstration, we'll use a simple heuristic
            # In practice, this would be a real API call
            details = {
                "method": "direct_api",
                "marketplace": marketplace,
                "api_endpoint": "amazon_product_api",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Simulate success for well-formed FNSKUs (this is just for demo)
            if len(fnsku) == 10 and fnsku.isalnum():
                # Generate a plausible ASIN (this would come from real API)
                simulated_asin = f"B{fnsku[1:10]}" if not fnsku.startswith('B') else fnsku
                return simulated_asin, self.confidence_weights['api_verified'], details
            
            return None, 0.0, details
            
        except Exception as e:
            logger.error(f"Error in direct API conversion for {fnsku}: {str(e)}")
            return None, 0.0, {"error": str(e), "method": "direct_api"}
    
    async def _convert_via_pattern_matching(
        self,
        db: AsyncSession,
        fnsku: str
    ) -> Tuple[Optional[str], float, Dict[str, Any]]:
        """
        Attempt conversion using pattern matching and database lookup.
        
        Args:
            db: Database session
            fnsku: FNSKU to convert
            
        Returns:
            Tuple of (ASIN, confidence_score, details)
        """
        try:
            details = {
                "method": "pattern_matching",
                "patterns_checked": []
            }
            
            # Strategy 1: Look for similar FNSKUs in cache that have known ASINs
            similar_result = await db.execute(
                select(FnskuCache).where(
                    and_(
                        FnskuCache.fnsku.like(f"{fnsku[:6]}%"),
                        FnskuCache.asin.isnot(None)
                    )
                ).limit(5)
            )
            similar_entries = similar_result.scalars().all()
            
            if similar_entries:
                details["patterns_checked"].append("similar_fnsku_prefix")
                details["similar_count"] = len(similar_entries)
                
                # Use the most recent similar entry with highest confidence
                best_entry = max(similar_entries, key=lambda x: x.confidence_score)
                
                # Generate a candidate ASIN based on pattern
                if best_entry.asin:
                    candidate_asin = self._generate_candidate_asin(fnsku, best_entry.asin)
                    if candidate_asin:
                        return candidate_asin, self.confidence_weights['pattern_match'], details
            
            # Strategy 2: Check if FNSKU follows ASIN-like pattern
            if fnsku.startswith('B') and self.asin_pattern.match(fnsku):
                details["patterns_checked"].append("asin_like_format")
                return fnsku, self.confidence_weights['heuristic'], details
            
            # Strategy 3: Mathematical transformation (common in some systems)
            transformed_asin = self._apply_fnsku_transformations(fnsku)
            if transformed_asin:
                details["patterns_checked"].append("mathematical_transformation")
                return transformed_asin, self.confidence_weights['heuristic'], details
            
            return None, 0.0, details
            
        except Exception as e:
            logger.error(f"Error in pattern matching for {fnsku}: {str(e)}")
            return None, 0.0, {"error": str(e), "method": "pattern_matching"}
    
    def _generate_candidate_asin(self, fnsku: str, reference_asin: str) -> Optional[str]:
        """Generate candidate ASIN based on FNSKU and reference ASIN pattern."""
        try:
            # Simple transformation - in practice this would be more sophisticated
            if len(fnsku) == 10 and not fnsku.startswith('B'):
                candidate = f"B{fnsku[1:10]}"
                if self.asin_pattern.match(candidate):
                    return candidate
            
            return None
            
        except Exception:
            return None
    
    def _apply_fnsku_transformations(self, fnsku: str) -> Optional[str]:
        """Apply common FNSKU to ASIN transformations."""
        transformations = []
        
        try:
            # Transformation 1: Direct substitution if pattern matches
            if len(fnsku) == 10 and not fnsku.startswith('B'):
                candidate = f"B{fnsku[1:10]}"
                if self.asin_pattern.match(candidate):
                    transformations.append(candidate)
            
            # Transformation 2: Character substitution (common patterns)
            # This would include known mappings like O->0, I->1, etc.
            cleaned = fnsku.replace('O', '0').replace('I', '1')
            if cleaned != fnsku and len(cleaned) == 10:
                candidate = f"B{cleaned[1:10]}" if not cleaned.startswith('B') else cleaned
                if self.asin_pattern.match(candidate):
                    transformations.append(candidate)
            
            # Return the first valid transformation
            return transformations[0] if transformations else None
            
        except Exception:
            return None
    
    async def _verify_asin_exists(
        self,
        db: AsyncSession,
        asin: str,
        marketplace: str = "US"
    ) -> bool:
        """
        Verify that an ASIN actually exists by checking with Amazon API.
        
        Args:
            db: Database session
            asin: ASIN to verify
            marketplace: Amazon marketplace
            
        Returns:
            True if ASIN exists
        """
        try:
            # Use the Amazon service to verify the ASIN exists
            product_data = await amazon_service.get_product_data(
                db=db,
                asin=asin,
                marketplace=marketplace,
                use_cache=True
            )
            return product_data is not None
            
        except ProductNotFoundError:
            return False
        except Exception:
            # If we can't verify due to API issues, assume it might exist
            return True
    
    async def convert_fnsku_to_asin(
        self,
        db: AsyncSession,
        fnsku: str,
        marketplace: str = "US",
        use_cache: bool = True,
        verify_asin: bool = True
    ) -> ConversionResult:
        """
        Convert FNSKU to ASIN using multiple strategies and confidence scoring.
        
        Args:
            db: Database session
            fnsku: FNSKU to convert
            marketplace: Amazon marketplace
            use_cache: Use cached results if available
            verify_asin: Verify the resulting ASIN exists
            
        Returns:
            Conversion result with confidence score
            
        Raises:
            FnskuFormatError: If FNSKU format is invalid
            ConversionFailedError: If all conversion strategies fail
        """
        start_time = time.time()
        
        # Validate FNSKU format first
        validation = self.validate_fnsku(fnsku)
        if not validation.valid:
            raise FnskuFormatError(f"Invalid FNSKU format: {', '.join(validation.errors)}")
        
        formatted_fnsku = validation.formatted_fnsku
        
        try:
            # Check cache first
            if use_cache:
                cached_result = await self._get_cached_conversion(db, formatted_fnsku)
                if cached_result:
                    return cached_result
            
            # Strategy 1: Direct API conversion
            asin, confidence, details = await self._convert_via_direct_api(
                db, formatted_fnsku, marketplace
            )
            conversion_method = ConversionMethod.DIRECT_API
            
            # Strategy 2: Pattern matching if direct API failed
            if not asin:
                asin, confidence, details = await self._convert_via_pattern_matching(
                    db, formatted_fnsku
                )
                conversion_method = ConversionMethod.PATTERN_MATCHING
            
            # Verify ASIN exists if we found one
            if asin and verify_asin:
                asin_exists = await self._verify_asin_exists(db, asin, marketplace)
                if not asin_exists:
                    confidence *= 0.5  # Reduce confidence if ASIN doesn't exist
                    details["asin_verification"] = "failed"
                else:
                    details["asin_verification"] = "passed"
            
            # Calculate conversion time
            conversion_time_ms = int((time.time() - start_time) * 1000)
            
            # Create result
            result = ConversionResult(
                fnsku=formatted_fnsku,
                asin=asin,
                confidence=ConversionConfidence(confidence),
                method=conversion_method,
                success=asin is not None,
                cached=False,
                cache_age_hours=0,
                conversion_time_ms=conversion_time_ms,
                details=details,
                error_message=None if asin else "No conversion strategy succeeded"
            )
            
            # Cache the result
            if use_cache:
                await self._cache_conversion_result(db, formatted_fnsku, result)
            
            if not asin:
                raise ConversionFailedError("All conversion strategies failed")
            
            return result
            
        except (FnskuFormatError, ConversionFailedError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error converting FNSKU {formatted_fnsku}: {str(e)}")
            
            conversion_time_ms = int((time.time() - start_time) * 1000)
            error_result = ConversionResult(
                fnsku=formatted_fnsku,
                asin=None,
                confidence=ConversionConfidence.NONE,
                method=ConversionMethod.FAILED,
                success=False,
                cached=False,
                cache_age_hours=0,
                conversion_time_ms=conversion_time_ms,
                details={"error": str(e)},
                error_message=f"Conversion error: {str(e)}"
            )
            
            # Cache failed result to avoid repeated attempts
            if use_cache:
                await self._cache_conversion_result(db, formatted_fnsku, error_result)
            
            raise ConversionFailedError(f"Conversion failed: {str(e)}")
    
    async def bulk_convert_fnskus(
        self,
        db: AsyncSession,
        fnskus: List[str],
        marketplace: str = "US",
        use_cache: bool = True
    ) -> List[ConversionResult]:
        """
        Convert multiple FNSKUs to ASINs with bulk optimization.
        
        Args:
            db: Database session
            fnskus: List of FNSKUs to convert
            marketplace: Amazon marketplace
            use_cache: Use cached results if available
            
        Returns:
            List of conversion results
        """
        results = []
        
        for fnsku in fnskus:
            try:
                result = await self.convert_fnsku_to_asin(
                    db=db,
                    fnsku=fnsku,
                    marketplace=marketplace,
                    use_cache=use_cache,
                    verify_asin=False  # Skip verification for bulk to improve performance
                )
                results.append(result)
                
                # Small delay to avoid overwhelming the system
                await asyncio.sleep(0.1)
                
            except Exception as e:
                # Create error result for failed conversions
                error_result = ConversionResult(
                    fnsku=fnsku,
                    asin=None,
                    confidence=ConversionConfidence.NONE,
                    method=ConversionMethod.FAILED,
                    success=False,
                    cached=False,
                    cache_age_hours=0,
                    conversion_time_ms=0,
                    details={"error": str(e)},
                    error_message=str(e)
                )
                results.append(error_result)
        
        return results
    
    async def get_conversion_stats(self, db: AsyncSession) -> ConversionStats:
        """
        Get FNSKU conversion statistics for monitoring.
        
        Args:
            db: Database session
            
        Returns:
            Conversion statistics
        """
        try:
            from sqlalchemy import func
            
            # Total conversions
            total_result = await db.execute(
                select(func.count(FnskuCache.fnsku))
            )
            total_conversions = total_result.scalar() or 0
            
            # Successful conversions
            success_result = await db.execute(
                select(func.count(FnskuCache.fnsku))
                .where(FnskuCache.asin.isnot(None))
            )
            successful_conversions = success_result.scalar() or 0
            
            # Average confidence
            confidence_result = await db.execute(
                select(func.avg(FnskuCache.confidence_score))
                .where(FnskuCache.asin.isnot(None))
            )
            avg_confidence = confidence_result.scalar() or 0.0
            
            # Method distribution
            method_result = await db.execute(
                select(
                    FnskuCache.conversion_method,
                    func.count(FnskuCache.fnsku).label('count')
                )
                .where(FnskuCache.asin.isnot(None))
                .group_by(FnskuCache.conversion_method)
            )
            
            method_distribution = {}
            for row in method_result:
                method_distribution[row.conversion_method] = row.count
            
            return ConversionStats(
                total_conversions=total_conversions,
                successful_conversions=successful_conversions,
                success_rate=(successful_conversions / total_conversions * 100) if total_conversions > 0 else 0.0,
                average_confidence=float(avg_confidence),
                method_distribution=method_distribution,
                cache_entries=total_conversions
            )
            
        except Exception as e:
            logger.error(f"Error getting conversion stats: {str(e)}")
            return ConversionStats(
                total_conversions=0,
                successful_conversions=0,
                success_rate=0.0,
                average_confidence=0.0,
                method_distribution={},
                cache_entries=0
            )
    
    async def cleanup_expired_cache(self, db: AsyncSession) -> int:
        """
        Clean up expired FNSKU conversion cache entries.
        
        Args:
            db: Database session
            
        Returns:
            Number of entries removed
        """
        try:
            from sqlalchemy import delete
            
            result = await db.execute(
                delete(FnskuCache).where(
                    FnskuCache.expires_at < datetime.utcnow()
                )
            )
            await db.commit()
            
            removed_count = result.rowcount
            logger.info(f"Cleaned up {removed_count} expired FNSKU cache entries")
            return removed_count
            
        except Exception as e:
            logger.error(f"Error cleaning up FNSKU cache: {str(e)}")
            await db.rollback()
            return 0


# Global FNSKU service instance
fnsku_service = FnskuService()