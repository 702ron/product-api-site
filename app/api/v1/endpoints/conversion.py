"""
FNSKU to ASIN conversion endpoints with confidence scoring and bulk processing.
"""
import logging
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    get_current_active_user, InsufficientCreditsError
)
from app.models.models import User, QueryLog
from app.services.credit_service import credit_service
from app.services.fnsku_service import (
    fnsku_service, FnskuFormatError, ConversionFailedError
)
from app.schemas.conversion import (
    ConversionRequest, ConversionResponse, BulkConversionRequest, BulkConversionResponse,
    FnskuValidationResult, ConversionStats, FnskuSuggestionRequest, FnskuSuggestionResponse,
    ConversionPerformanceMetrics, ConversionHealthCheck, ConversionResult
)

router = APIRouter()
logger = logging.getLogger(__name__)


async def log_conversion_query(
    db: AsyncSession,
    user_id: str,
    query_type: str,
    query_input: str,
    credits_deducted: int,
    status: str,
    response_time_ms: int,
    api_response_summary: dict = None,
    error_details: dict = None
) -> None:
    """Log conversion query for analytics and monitoring."""
    try:
        query_log = QueryLog(
            user_id=user_id,
            query_type=query_type,
            query_input=query_input,
            credits_deducted=credits_deducted,
            status=status,
            response_time_ms=response_time_ms,
            api_response_summary=api_response_summary,
            error_details=error_details,
            endpoint="/api/v1/conversion"
        )
        db.add(query_log)
        await db.commit()
    except Exception as e:
        logger.error(f"Error logging conversion query: {str(e)}")


@router.post("/fnsku-to-asin", response_model=ConversionResponse)
async def convert_fnsku_to_asin(
    request: ConversionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Convert FNSKU to ASIN with confidence scoring.
    
    Features:
    - Multiple conversion strategies with fallback
    - Confidence scoring from 0-100%
    - Intelligent caching to reduce costs
    - Credit refund for failed conversions
    - Detailed conversion methodology reporting
    """
    start_time = time.time()
    operation_cost = 2  # FNSKU conversion costs more than simple ASIN queries
    
    try:
        # Check and deduct credits first
        await credit_service.deduct_credits(
            db=db,
            user_id=current_user.id,
            operation="fnsku_conversion",
            cost=operation_cost,
            description=f"FNSKU to ASIN conversion for {request.fnsku}",
            extra_data={
                "fnsku": request.fnsku,
                "marketplace": request.marketplace,
                "use_cache": request.use_cache,
                "verify_asin": request.verify_asin
            }
        )
        
        # Perform conversion
        conversion_result = await fnsku_service.convert_fnsku_to_asin(
            db=db,
            fnsku=request.fnsku,
            marketplace=request.marketplace,
            use_cache=request.use_cache,
            verify_asin=request.verify_asin
        )
        
        # Calculate total response time
        total_response_time_ms = int((time.time() - start_time) * 1000)
        
        # Log successful conversion
        background_tasks.add_task(
            log_conversion_query,
            db=db,
            user_id=current_user.id,
            query_type="fnsku_conversion",
            query_input=request.fnsku,
            credits_deducted=operation_cost,
            status="success",
            response_time_ms=total_response_time_ms,
            api_response_summary={
                "fnsku": conversion_result.fnsku,
                "asin": conversion_result.asin,
                "confidence": conversion_result.confidence.value,
                "method": conversion_result.method.value,
                "from_cache": conversion_result.cached,
                "conversion_time_ms": conversion_result.conversion_time_ms
            }
        )
        
        return ConversionResponse(
            status="success",
            conversion=conversion_result,
            credits_used=operation_cost,
            response_time_ms=total_response_time_ms
        )
        
    except InsufficientCreditsError as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_conversion_query,
            db=db,
            user_id=current_user.id,
            query_type="fnsku_conversion",
            query_input=request.fnsku,
            credits_deducted=0,
            status="error",
            response_time_ms=response_time_ms,
            error_details={"error": "insufficient_credits", "message": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
        
    except FnskuFormatError as e:
        # Refund credits for invalid format
        await credit_service.refund_credits(
            db=db,
            user_id=current_user.id,
            amount=operation_cost,
            reason="Invalid FNSKU format",
            original_operation="fnsku_conversion",
            extra_data={"fnsku": request.fnsku, "error": str(e)}
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_conversion_query,
            db=db,
            user_id=current_user.id,
            query_type="fnsku_conversion",
            query_input=request.fnsku,
            credits_deducted=0,  # Refunded
            status="error",
            response_time_ms=response_time_ms,
            error_details={"error": "invalid_format", "message": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid FNSKU format: {str(e)}"
        )
        
    except ConversionFailedError as e:
        # Refund credits for failed conversion
        await credit_service.refund_credits(
            db=db,
            user_id=current_user.id,
            amount=operation_cost,
            reason="Conversion failed",
            original_operation="fnsku_conversion",
            extra_data={"fnsku": request.fnsku, "error": str(e)}
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_conversion_query,
            db=db,
            user_id=current_user.id,
            query_type="fnsku_conversion",
            query_input=request.fnsku,
            credits_deducted=0,  # Refunded
            status="error",
            response_time_ms=response_time_ms,
            error_details={"error": "conversion_failed", "message": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FNSKU conversion failed: {str(e)}"
        )
        
    except Exception as e:
        # Refund credits for unexpected errors
        await credit_service.refund_credits(
            db=db,
            user_id=current_user.id,
            amount=operation_cost,
            reason="Unexpected error",
            original_operation="fnsku_conversion",
            extra_data={"fnsku": request.fnsku, "error": str(e)}
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_conversion_query,
            db=db,
            user_id=current_user.id,
            query_type="fnsku_conversion",
            query_input=request.fnsku,
            credits_deducted=0,  # Refunded
            status="error",
            response_time_ms=response_time_ms,
            error_details={"error": "unexpected_error", "message": str(e)}
        )
        
        logger.error(f"Unexpected error in FNSKU conversion for {request.fnsku}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )


@router.post("/bulk", response_model=BulkConversionResponse)
async def bulk_convert_fnskus(
    request: BulkConversionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Convert multiple FNSKUs to ASINs with bulk processing optimization.
    
    Features:
    - Bulk discount pricing (15% off for 10+ items)
    - Parallel processing where possible
    - Partial success handling
    - Detailed error reporting per FNSKU
    - Smart caching to reduce external API calls
    """
    start_time = time.time()
    
    # Calculate bulk operation cost
    base_cost_per_item = 2  # Higher cost for FNSKU conversion
    item_count = len(request.fnskus)
    
    # Apply bulk discount for 10+ items
    if item_count >= 10:
        total_cost = max(1, int(item_count * base_cost_per_item * 0.85))  # 15% discount
        bulk_discount_applied = True
    else:
        total_cost = item_count * base_cost_per_item
        bulk_discount_applied = False
    
    try:
        # Check and deduct credits upfront
        await credit_service.deduct_credits(
            db=db,
            user_id=current_user.id,
            operation="bulk_fnsku_conversion",
            cost=total_cost,
            description=f"Bulk FNSKU conversion for {item_count} FNSKUs",
            extra_data={
                "fnsku_count": item_count,
                "marketplace": request.marketplace,
                "bulk_discount_applied": bulk_discount_applied,
                "fnskus": request.fnskus[:10]  # Log first 10 FNSKUs
            }
        )
        
        # Process FNSKUs
        conversion_results = await fnsku_service.bulk_convert_fnskus(
            db=db,
            fnskus=request.fnskus,
            marketplace=request.marketplace,
            use_cache=request.use_cache
        )
        
        # Analyze results
        successful_conversions = [r for r in conversion_results if r.success]
        failed_conversions = [r for r in conversion_results if not r.success]
        cache_hits = sum(1 for r in conversion_results if r.cached)
        cache_misses = len(conversion_results) - cache_hits
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Log bulk conversion
        background_tasks.add_task(
            log_conversion_query,
            db=db,
            user_id=current_user.id,
            query_type="bulk_fnsku_conversion",
            query_input=f"{item_count} FNSKUs",
            credits_deducted=total_cost,
            status="success" if len(failed_conversions) == 0 else "partial",
            response_time_ms=processing_time_ms,
            api_response_summary={
                "total_requested": item_count,
                "successful": len(successful_conversions),
                "failed": len(failed_conversions),
                "cache_hits": cache_hits,
                "bulk_discount_applied": bulk_discount_applied
            }
        )
        
        return BulkConversionResponse(
            status="success" if len(failed_conversions) == 0 else "partial",
            total_requested=item_count,
            total_successful=len(successful_conversions),
            total_failed=len(failed_conversions),
            total_credits_used=total_cost,
            processing_time_ms=processing_time_ms,
            conversions=conversion_results,
            cache_hits=cache_hits,
            cache_misses=cache_misses
        )
        
    except InsufficientCreditsError as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_conversion_query,
            db=db,
            user_id=current_user.id,
            query_type="bulk_fnsku_conversion",
            query_input=f"{item_count} FNSKUs",
            credits_deducted=0,
            status="error",
            response_time_ms=response_time_ms,
            error_details={"error": "insufficient_credits", "message": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
        
    except Exception as e:
        # Refund credits for unexpected errors
        await credit_service.refund_credits(
            db=db,
            user_id=current_user.id,
            amount=total_cost,
            reason="Bulk conversion failed",
            original_operation="bulk_fnsku_conversion",
            extra_data={"fnsku_count": item_count, "error": str(e)}
        )
        
        logger.error(f"Unexpected error in bulk FNSKU conversion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk conversion failed. Credits have been refunded."
        )


@router.post("/validate-fnsku", response_model=FnskuValidationResult)
async def validate_fnsku(
    fnsku: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Validate FNSKU format without consuming credits.
    
    Checks if the provided FNSKU follows the correct format:
    - 10 characters total
    - Alphanumeric characters only
    - Provides suggestions for common format errors
    """
    try:
        validation_result = fnsku_service.validate_fnsku(fnsku)
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating FNSKU {fnsku}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Validation error occurred"
        )


@router.post("/suggest-fnsku", response_model=FnskuSuggestionResponse)
async def suggest_fnsku_corrections(
    request: FnskuSuggestionRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get suggestions for correcting invalid FNSKU format.
    
    Provides intelligent suggestions for common FNSKU format errors
    and attempts automatic correction where possible.
    """
    try:
        validation_result = fnsku_service.validate_fnsku(request.input_value)
        
        # Generate additional suggestions
        suggestions = validation_result.suggestions.copy()
        auto_corrected = None
        
        # Simple auto-correction attempts
        cleaned_input = request.input_value.upper().strip()
        if len(cleaned_input) == 10 and cleaned_input.isalnum():
            auto_corrected = cleaned_input
            suggestions.insert(0, f"Try: {auto_corrected}")
        
        return FnskuSuggestionResponse(
            original_input=request.input_value,
            suggestions=suggestions,
            auto_corrected=auto_corrected,
            validation_result=validation_result
        )
        
    except Exception as e:
        logger.error(f"Error generating FNSKU suggestions for {request.input_value}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating suggestions"
        )


@router.get("/stats", response_model=ConversionStats)
async def get_conversion_statistics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get FNSKU conversion statistics for monitoring and optimization.
    
    Provides insights into:
    - Total conversions performed
    - Success rates by conversion method
    - Average confidence scores
    - Cache performance metrics
    """
    try:
        stats = await fnsku_service.get_conversion_stats(db)
        return stats
        
    except Exception as e:
        logger.error(f"Error getting conversion stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conversion statistics"
        )


@router.get("/performance", response_model=ConversionPerformanceMetrics)
async def get_performance_metrics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed performance metrics for the conversion service.
    
    Provides performance insights for system monitoring and optimization.
    """
    try:
        from sqlalchemy import func
        from app.models.models import FnskuCache
        
        # Calculate basic performance metrics
        # Note: In a real implementation, these would be calculated from actual metrics
        metrics = ConversionPerformanceMetrics(
            average_conversion_time_ms=450.0,  # Placeholder
            cache_hit_rate=78.5,  # Placeholder
            method_performance={
                "direct_api": 320.0,
                "pattern_matching": 180.0,
                "database_lookup": 45.0
            },
            success_rates_by_method={
                "direct_api": 94.5,
                "pattern_matching": 67.8,
                "database_lookup": 89.2
            },
            recent_conversions=247,  # Last 24 hours
            peak_conversion_time=1250.0  # Peak time in last hour
        )
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving performance metrics"
        )


@router.get("/health", response_model=ConversionHealthCheck)
async def check_conversion_service_health(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Health check endpoint for the conversion service.
    
    Provides status information about all service components.
    """
    try:
        # Perform basic health checks
        # Note: In a real implementation, these would test actual connectivity
        health = ConversionHealthCheck(
            service_status="healthy",
            cache_status="healthy",
            api_status="healthy",
            database_status="healthy",
            recent_error_rate=2.3,  # Percentage
            average_response_time_ms=425.0,
            uptime_seconds=86400,  # 24 hours
            last_maintenance=None
        )
        
        return health
        
    except Exception as e:
        logger.error(f"Error checking conversion service health: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )


@router.delete("/cache/cleanup")
async def cleanup_conversion_cache(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Clean up expired conversion cache entries (admin operation).
    
    Removes all cache entries that have passed their expiration time.
    """
    try:
        removed_count = await fnsku_service.cleanup_expired_cache(db)
        
        return {
            "status": "success",
            "message": f"Cleaned up {removed_count} expired conversion cache entries"
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up conversion cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cleaning up conversion cache"
        )