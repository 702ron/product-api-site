"""
Amazon product data endpoints for ASIN queries and product information retrieval.
"""
import logging
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    get_current_active_user, InsufficientCreditsError, verify_user_has_credits
)
from app.models.models import User, QueryLog
from app.services.credit_service import credit_service
from app.services.amazon_service import (
    amazon_service, ProductNotFoundError, RateLimitExceededError, ExternalAPIError
)
from app.services.input_detection_service import input_detector, InputType
from app.services.fnsku_service import fnsku_service
from app.schemas.products import (
    ProductRequest, ProductResponse, BulkProductRequest, BulkProductResponse,
    ProductData, ProductValidationResponse, ProductCacheStats, Marketplace,
    MultiLookupRequest, MultiLookupResponse, ProductSearchRequest, ProductSearchResponse
)
from app.schemas.jobs import BulkProductJobRequest, JobSubmissionResponse

router = APIRouter()
logger = logging.getLogger(__name__)


async def log_query(
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
    """Log API query for analytics and monitoring."""
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
            endpoint="/api/v1/products"
        )
        db.add(query_log)
        await db.commit()
    except Exception as e:
        logger.error(f"Error logging query: {str(e)}")


@router.post("/asin", response_model=ProductResponse)
async def get_product_by_asin(
    request: ProductRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive Amazon product data by ASIN.
    
    Retrieves product information including:
    - Title, brand, manufacturer
    - Pricing and availability
    - Customer ratings and reviews
    - Product images
    - Features and description
    - Category information
    
    Uses intelligent caching to minimize external API calls and costs.
    """
    start_time = time.time()
    operation_cost = 1  # Base cost for ASIN query
    
    try:
        # Calculate operation cost based on request complexity
        if request.include_reviews:
            operation_cost += 1
        if request.include_offers:
            operation_cost += 1
        
        # Check and deduct credits first
        await credit_service.deduct_credits(
            db=db,
            user_id=current_user.id,
            operation="asin_query",
            cost=operation_cost,
            description=f"Product data query for ASIN {request.asin}",
            extra_data={
                "asin": request.asin,
                "marketplace": request.marketplace.value,
                "include_reviews": request.include_reviews,
                "include_offers": request.include_offers
            }
        )
        
        # Get product data
        product_data = await amazon_service.get_product_data(
            db=db,
            asin=request.asin,
            marketplace=request.marketplace.value,
            include_reviews=request.include_reviews,
            use_cache=request.use_cache
        )
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Log successful query
        background_tasks.add_task(
            log_query,
            db=db,
            user_id=current_user.id,
            query_type="asin_query",
            query_input=request.asin,
            credits_deducted=operation_cost,
            status="success",
            response_time_ms=response_time_ms,
            api_response_summary={
                "asin": product_data.asin,
                "title": product_data.title,
                "brand": product_data.brand,
                "price": product_data.price.amount if product_data.price else None,
                "rating": product_data.rating.value if product_data.rating else None,
                "data_source": product_data.data_source.value,
                "from_cache": product_data.data_source.value == "cache"
            }
        )
        
        return ProductResponse(
            status="success",
            credits_used=operation_cost,
            response_time_ms=response_time_ms,
            data=product_data,
            from_cache=product_data.data_source.value == "cache",
            cache_age_seconds=None  # Could calculate if needed
        )
        
    except InsufficientCreditsError as e:
        # Log failed query due to insufficient credits
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_query,
            db=db,
            user_id=current_user.id,
            query_type="asin_query",
            query_input=request.asin,
            credits_deducted=0,
            status="error",
            response_time_ms=response_time_ms,
            error_details={"error": "insufficient_credits", "message": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
        
    except ProductNotFoundError as e:
        # Refund credits for not found products
        await credit_service.refund_credits(
            db=db,
            user_id=current_user.id,
            amount=operation_cost,
            reason="Product not found",
            original_operation="asin_query",
            extra_data={"asin": request.asin, "marketplace": request.marketplace.value}
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_query,
            db=db,
            user_id=current_user.id,
            query_type="asin_query",
            query_input=request.asin,
            credits_deducted=0,  # Refunded
            status="error",
            response_time_ms=response_time_ms,
            error_details={"error": "product_not_found", "message": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product not found: {str(e)}"
        )
        
    except RateLimitExceededError as e:
        # Refund credits for rate limit errors
        await credit_service.refund_credits(
            db=db,
            user_id=current_user.id,
            amount=operation_cost,
            reason="Rate limit exceeded",
            original_operation="asin_query",
            extra_data={"asin": request.asin, "marketplace": request.marketplace.value}
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_query,
            db=db,
            user_id=current_user.id,
            query_type="asin_query", 
            query_input=request.asin,
            credits_deducted=0,  # Refunded
            status="error",
            response_time_ms=response_time_ms,
            error_details={"error": "rate_limit_exceeded", "message": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
        
    except ExternalAPIError as e:
        # Refund credits for external API errors
        await credit_service.refund_credits(
            db=db,
            user_id=current_user.id,
            amount=operation_cost,
            reason="External API error",
            original_operation="asin_query",
            extra_data={"asin": request.asin, "error": str(e)}
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_query,
            db=db,
            user_id=current_user.id,
            query_type="asin_query",
            query_input=request.asin,
            credits_deducted=0,  # Refunded
            status="error",
            response_time_ms=response_time_ms,
            error_details={"error": "external_api_error", "message": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="External service temporarily unavailable. Please try again later."
        )
        
    except Exception as e:
        # Refund credits for unexpected errors
        await credit_service.refund_credits(
            db=db,
            user_id=current_user.id,
            amount=operation_cost,
            reason="Unexpected error",
            original_operation="asin_query",
            extra_data={"asin": request.asin, "error": str(e)}
        )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_query,
            db=db,
            user_id=current_user.id,
            query_type="asin_query",
            query_input=request.asin,
            credits_deducted=0,  # Refunded
            status="error",
            response_time_ms=response_time_ms,
            error_details={"error": "unexpected_error", "message": str(e)}
        )
        
        logger.error(f"Unexpected error in product query for {request.asin}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )


@router.post("/bulk-async", response_model=dict)
async def get_bulk_products_async(
    request: BulkProductJobRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit bulk product query job for asynchronous processing.
    
    Features:
    - Queue-based processing with progress tracking
    - Bulk discount pricing (10% off for 10+ items)
    - Parallel processing with rate limiting
    - Job status monitoring via /api/v1/jobs/status/{job_id}
    
    Returns job_id for status tracking instead of immediate results.
    """
    from app.core.queue import get_queue, JobPriority
    from app.schemas.jobs import JobSubmissionResponse
    
    try:
        # Validate input
        if len(request.asins) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 1000 ASINs allowed per bulk request"
            )
        
        # Calculate cost and check credits
        base_cost_per_item = 1
        item_count = len(request.asins)
        
        # Apply bulk discount for 10+ items
        if item_count >= 10:
            total_cost = max(1, int(item_count * base_cost_per_item * 0.9))
            bulk_discount_applied = True
        else:
            total_cost = item_count * base_cost_per_item
            bulk_discount_applied = False
        
        # Check user has sufficient credits
        user_credits = await credit_service.get_user_credits(str(current_user.id), db)
        if user_credits < total_cost:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits. Required: {total_cost}, Available: {user_credits}"
            )
        
        # Prepare job payload
        payload = {
            "asins": request.asins,
            "marketplace": request.marketplace,
            "total_cost": total_cost,
            "bulk_discount_applied": bulk_discount_applied
        }
        
        # Submit job to queue
        queue = await get_queue()
        job_id = await queue.enqueue(
            job_type="bulk_products",
            user_id=str(current_user.id),
            payload=payload,
            priority=request.priority,
            max_retries=request.max_retries
        )
        
        # Estimate processing time (rough calculation)
        estimated_minutes = max(1, item_count // 20)  # ~20 items per minute
        
        return JobSubmissionResponse(
            job_id=job_id,
            message=f"Bulk product query job submitted for {item_count} ASINs",
            estimated_processing_time_minutes=estimated_minutes,
            status_url=f"/api/v1/jobs/status/{job_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting bulk products job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit bulk products job"
        )


@router.post("/bulk", response_model=BulkProductResponse)
async def get_bulk_products(
    request: BulkProductRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    DEPRECATED: Use /bulk-async for better performance.
    
    Get product data for multiple ASINs with bulk processing optimization.
    
    Features:
    - Bulk discount pricing (10% off for 10+ items)
    - Parallel processing where possible
    - Partial success handling
    - Detailed error reporting per ASIN
    
    Note: This endpoint processes synchronously and may timeout for large requests.
    For >50 ASINs, use /bulk-async instead.
    """
    start_time = time.time()
    
    # Calculate bulk operation cost
    base_cost_per_item = 1
    item_count = len(request.asins)
    
    # Apply bulk discount for 10+ items
    if item_count >= 10:
        total_cost = max(1, int(item_count * base_cost_per_item * 0.9))  # 10% discount
        bulk_discount_applied = True
    else:
        total_cost = item_count * base_cost_per_item
        bulk_discount_applied = False
    
    try:
        # Check and deduct credits upfront
        await credit_service.deduct_credits(
            db=db,
            user_id=current_user.id,
            operation="bulk_asin_query",
            cost=total_cost,
            description=f"Bulk product query for {item_count} ASINs",
            extra_data={
                "asin_count": item_count,
                "marketplace": request.marketplace.value,
                "bulk_discount_applied": bulk_discount_applied,
                "asins": request.asins[:10]  # Log first 10 ASINs
            }
        )
        
        # Process ASINs
        successful_products = []
        errors = []
        cache_hits = 0
        cache_misses = 0
        
        for asin in request.asins:
            try:
                product_data = await amazon_service.get_product_data(
                    db=db,
                    asin=asin,
                    marketplace=request.marketplace.value,
                    include_reviews=request.include_reviews,
                    use_cache=request.use_cache
                )
                
                successful_products.append(product_data)
                
                if product_data.data_source.value == "cache":
                    cache_hits += 1
                else:
                    cache_misses += 1
                    
            except ProductNotFoundError:
                errors.append({
                    "asin": asin,
                    "error": "product_not_found",
                    "message": f"Product {asin} not found"
                })
            except Exception as e:
                errors.append({
                    "asin": asin,
                    "error": "processing_error",
                    "message": str(e)
                })
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Log bulk query
        background_tasks.add_task(
            log_query,
            db=db,
            user_id=current_user.id,
            query_type="bulk_asin_query",
            query_input=f"{item_count} ASINs",
            credits_deducted=total_cost,
            status="success" if successful_products else "partial",
            response_time_ms=processing_time_ms,
            api_response_summary={
                "total_requested": item_count,
                "successful": len(successful_products),
                "errors": len(errors),
                "cache_hits": cache_hits,
                "bulk_discount_applied": bulk_discount_applied
            }
        )
        
        return BulkProductResponse(
            status="success" if len(errors) == 0 else "partial",
            total_requested=item_count,
            total_processed=len(successful_products),
            total_credits_used=total_cost,
            processing_time_ms=processing_time_ms,
            products=successful_products,
            errors=errors,
            cache_hits=cache_hits,
            cache_misses=cache_misses
        )
        
    except InsufficientCreditsError as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_query,
            db=db,
            user_id=current_user.id,
            query_type="bulk_asin_query",
            query_input=f"{item_count} ASINs",
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
            reason="Bulk operation failed",
            original_operation="bulk_asin_query",
            extra_data={"asin_count": item_count, "error": str(e)}
        )
        
        logger.error(f"Unexpected error in bulk query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk operation failed. Credits have been refunded."
        )


@router.post("/validate-asin", response_model=ProductValidationResponse)
async def validate_asin(
    asin: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Validate ASIN format without consuming credits.
    
    Checks if the provided ASIN follows the correct format:
    - 10 characters total
    - Starts with 'B'
    - Followed by 9 alphanumeric characters
    """
    try:
        is_valid = await amazon_service.validate_asin(asin)
        formatted_asin = asin.upper() if is_valid else None
        
        errors = []
        if not is_valid:
            errors.append("ASIN must be 10 characters starting with 'B' followed by 9 alphanumeric characters")
        
        return ProductValidationResponse(
            asin=asin,
            valid=is_valid,
            formatted_asin=formatted_asin,
            errors=errors
        )
        
    except Exception as e:
        logger.error(f"Error validating ASIN {asin}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Validation error occurred"
        )


@router.get("/cache-stats", response_model=ProductCacheStats)
async def get_cache_statistics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get product cache statistics for monitoring and optimization.
    
    Provides insights into:
    - Total cached products
    - Cache hit rates  
    - Average cache age
    - Distribution by marketplace
    """
    try:
        from sqlalchemy import func, case
        from app.models.models import ProductCache
        
        # Get total cached products
        total_result = await db.execute(
            select(func.count(ProductCache.asin))
        )
        total_cached = total_result.scalar() or 0
        
        # Get expired entries
        expired_result = await db.execute(
            select(func.count(ProductCache.asin))
            .where(ProductCache.expires_at < func.now())
        )
        expired_entries = expired_result.scalar() or 0
        
        # Get marketplaces distribution
        marketplace_result = await db.execute(
            select(
                ProductCache.marketplace,
                func.count(ProductCache.asin).label('count')
            )
            .group_by(ProductCache.marketplace)
        )
        
        marketplaces = {}
        for row in marketplace_result:
            marketplaces[row.marketplace] = row.count
        
        # Calculate average cache age (simplified)
        avg_age_hours = 12.0  # Placeholder - could calculate actual average
        
        # Calculate cache hit rate (simplified - would need actual metrics)
        cache_hit_rate = 75.0  # Placeholder - would calculate from query logs
        
        return ProductCacheStats(
            total_cached_products=total_cached,
            cache_hit_rate=cache_hit_rate,
            average_cache_age_hours=avg_age_hours,
            expired_entries=expired_entries,
            marketplaces=marketplaces
        )
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving cache statistics"
        )


@router.delete("/cache/cleanup")
async def cleanup_expired_cache(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Clean up expired cache entries (admin operation).
    
    Removes all cache entries that have passed their expiration time.
    """
    try:
        removed_count = await amazon_service.cleanup_expired_cache(db)
        
        return {
            "status": "success",
            "message": f"Cleaned up {removed_count} expired cache entries"
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cleaning up cache"
        )


@router.post("/multi-lookup", response_model=MultiLookupResponse)
async def multi_input_lookup(
    request: MultiLookupRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Multi-input product lookup supporting ASIN, FNSKU, and GTIN/UPC.
    
    Automatically detects input type and routes to appropriate API:
    - ASIN: Direct product lookup (1 credit)
    - FNSKU: Two-step conversion FNSKU→ASIN→Product (10 credits)
    - GTIN/UPC: Barcode-based product lookup (1 credit)
    
    Features:
    - Smart input type detection with manual override
    - Variable credit costs based on complexity
    - Comprehensive error handling with credit refunds
    - Detailed logging and monitoring
    """
    start_time = time.time()
    detection_result = None
    credits_used = 0
    conversion_data = None
    
    try:
        # Detect input type (with manual override if specified)
        if request.manual_type:
            try:
                manual_input_type = InputType(request.manual_type)
                detection_result = input_detector.validate_manual_override(
                    request.input_value, manual_input_type
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Manual type override invalid: {str(e)}"
                )
        else:
            detection_result = input_detector.detect_input_type(request.input_value)
        
        # Check for validation errors
        if detection_result.validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input validation failed: {', '.join(detection_result.validation_errors)}"
            )
        
        # Get credit cost for this input type
        operation_cost = detection_result.credit_cost
        
        # Apply additional costs for extra features
        if request.include_reviews:
            operation_cost += 1
        if request.include_offers:
            operation_cost += 1
        
        # Check and deduct credits first
        await credit_service.deduct_credits(
            db=db,
            user_id=current_user.id,
            operation=f"{detection_result.input_type.value}_lookup",
            cost=operation_cost,
            description=f"Multi-input lookup for {detection_result.input_type.value}: {detection_result.input_value}",
            extra_data={
                "input_type": detection_result.input_type.value,
                "input_value": detection_result.input_value,
                "marketplace": request.marketplace.value,
                "detection_confidence": detection_result.confidence,
                "include_reviews": request.include_reviews,
                "include_offers": request.include_offers
            }
        )
        
        credits_used = operation_cost
        product_data = None
        
        # Route to appropriate lookup method based on input type
        if detection_result.input_type == InputType.ASIN:
            # Direct ASIN lookup
            product_data = await amazon_service.get_product_data(
                db=db,
                asin=detection_result.input_value,
                marketplace=request.marketplace.value,
                include_reviews=request.include_reviews,
                use_cache=True
            )
            
        elif detection_result.input_type == InputType.FNSKU:
            # Two-step FNSKU conversion
            logger.info(f"Converting FNSKU {detection_result.input_value} to ASIN")
            
            # First step: Convert FNSKU to ASIN
            conversion_result = await fnsku_service.convert_fnsku_to_asin(
                db=db,
                fnsku=detection_result.input_value,
                marketplace=request.marketplace.value
            )
            
            if not conversion_result.asin:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Could not convert FNSKU {detection_result.input_value} to ASIN"
                )
            
            # Store conversion data for response
            conversion_data = {
                "fnsku": detection_result.input_value,
                "asin": conversion_result.asin,
                "confidence": conversion_result.confidence.value,
                "method": conversion_result.method.value,
                "from_cache": conversion_result.from_cache
            }
            
            # Second step: Get product data using converted ASIN
            product_data = await amazon_service.get_product_data(
                db=db,
                asin=conversion_result.asin,
                marketplace=request.marketplace.value,
                include_reviews=request.include_reviews,
                use_cache=True
            )
            
        elif detection_result.input_type == InputType.GTIN_UPC:
            # GTIN/UPC barcode lookup
            logger.info(f"Looking up product by GTIN/UPC {detection_result.input_value}")
            
            # Use ASIN Data API's barcode lookup capability
            product_data = await amazon_service.get_product_by_barcode(
                db=db,
                barcode=detection_result.input_value,
                marketplace=request.marketplace.value,
                include_reviews=request.include_reviews,
                use_cache=True
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported input type: {detection_result.input_type}"
            )
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Log successful query
        background_tasks.add_task(
            log_query,
            db=db,
            user_id=current_user.id,
            query_type=f"{detection_result.input_type.value}_lookup",
            query_input=detection_result.input_value,
            credits_deducted=credits_used,
            status="success",
            response_time_ms=response_time_ms,
            api_response_summary={
                "input_type": detection_result.input_type.value,
                "input_value": detection_result.input_value,
                "asin": product_data.asin if product_data else None,
                "title": product_data.title if product_data else None,
                "brand": product_data.brand if product_data else None,
                "price": product_data.price.amount if product_data and product_data.price else None,
                "rating": product_data.rating.value if product_data and product_data.rating else None,
                "data_source": product_data.data_source.value if product_data else None,
                "detection_confidence": detection_result.confidence,
                "conversion_used": conversion_data is not None
            }
        )
        
        return MultiLookupResponse(
            status="success",
            input_type=detection_result.input_type.value,
            input_value=detection_result.input_value,
            credits_used=credits_used,
            processing_time_ms=response_time_ms,
            product=product_data,
            conversion_data=conversion_data,
            detection_confidence=detection_result.confidence,
            validation_warnings=detection_result.validation_errors or []
        )
        
    except InsufficientCreditsError as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_query,
            db=db,
            user_id=current_user.id,
            query_type=f"{detection_result.input_type.value}_lookup" if detection_result else "multi_lookup",
            query_input=request.input_value,
            credits_deducted=0,
            status="error",
            response_time_ms=response_time_ms,
            error_details={"error": "insufficient_credits", "message": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors, etc.)
        raise
        
    except ProductNotFoundError as e:
        # Refund credits for product not found
        if credits_used > 0:
            await credit_service.refund_credits(
                db=db,
                user_id=current_user.id,
                amount=credits_used,
                reason="Product not found",
                original_operation=f"{detection_result.input_type.value}_lookup" if detection_result else "multi_lookup",
                extra_data={
                    "input_type": detection_result.input_type.value if detection_result else "unknown",
                    "input_value": request.input_value,
                    "marketplace": request.marketplace.value
                }
            )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_query,
            db=db,
            user_id=current_user.id,
            query_type=f"{detection_result.input_type.value}_lookup" if detection_result else "multi_lookup",
            query_input=request.input_value,
            credits_deducted=0,  # Credits refunded
            status="error",
            response_time_ms=response_time_ms,
            error_details={"error": "product_not_found", "message": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product not found: {str(e)}. Credits have been refunded."
        )
        
    except Exception as e:
        # Refund credits for unexpected errors
        if credits_used > 0:
            await credit_service.refund_credits(
                db=db,
                user_id=current_user.id,
                amount=credits_used,
                reason="Lookup operation failed",
                original_operation=f"{detection_result.input_type.value}_lookup" if detection_result else "multi_lookup",
                extra_data={
                    "input_type": detection_result.input_type.value if detection_result else "unknown",
                    "input_value": request.input_value,
                    "error": str(e)
                }
            )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_query,
            db=db,
            user_id=current_user.id,
            query_type=f"{detection_result.input_type.value}_lookup" if detection_result else "multi_lookup",
            query_input=request.input_value,
            credits_deducted=0,  # Credits refunded
            status="error",
            response_time_ms=response_time_ms,
            error_details={"error": "processing_error", "message": str(e)}
        )
        
        logger.error(f"Unexpected error in multi-lookup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lookup operation failed. Credits have been refunded."
        )


@router.post("/search", response_model=ProductSearchResponse)
async def search_products(
    request: ProductSearchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for products by name with pagination support.
    
    Returns a list of matching products with key details (title, ASIN, price, rating, image).
    Users can then select a specific ASIN to get full product details via the regular ASIN lookup.
    
    Features:
    - Paginated search results (1 credit per page)
    - Maximum 5 pages per request (API limitation)
    - Search suggestions for better results
    - Comprehensive product list with key details
    
    Credit cost: 1 credit per page retrieved (variable total based on pages requested)
    """
    start_time = time.time()
    credits_used = 0
    pages_retrieved = 0
    
    try:
        # Validate and cap pagination parameters
        max_page = min(request.max_page, 5)  # API enforced maximum
        page = max(request.page, 1)  # Ensure minimum page 1
        
        # Calculate expected credit cost (may be less if fewer pages available)
        expected_credits = max_page
        
        # Check credits upfront for maximum possible cost
        await credit_service.deduct_credits(
            db=db,
            user_id=current_user.id,
            operation="product_search",
            cost=expected_credits,
            description=f"Product search: '{request.search_term}' ({max_page} pages max)",
            extra_data={
                "search_term": request.search_term,
                "marketplace": request.marketplace.value,
                "page": page,
                "max_page": max_page
            }
        )
        
        credits_used = expected_credits
        
        # Perform the search
        search_response = await amazon_service.search_products(
            search_term=request.search_term,
            marketplace=request.marketplace.value,
            page=page,
            max_page=max_page,
            include_reviews=False  # Search results don't need full reviews
        )
        
        # Extract results and pagination info
        raw_results = search_response.get("search_results", [])
        api_pagination = search_response.get("pagination", {})
        
        # Calculate actual pages retrieved (for accurate credit calculation)
        pages_retrieved = len(set(result.get("page", 1) for result in raw_results)) if raw_results else 1
        pages_retrieved = min(pages_retrieved, max_page)  # Cap at requested max
        
        # Refund excess credits if fewer pages were actually retrieved
        if pages_retrieved < expected_credits:
            refund_amount = expected_credits - pages_retrieved
            await credit_service.refund_credits(
                db=db,
                user_id=current_user.id,
                amount=refund_amount,
                reason="Fewer search pages available than requested",
                original_operation="product_search",
                extra_data={
                    "search_term": request.search_term,
                    "requested_pages": max_page,
                    "actual_pages": pages_retrieved
                }
            )
            credits_used = pages_retrieved
        
        # Parse and structure search results
        structured_results = []
        for result in raw_results:
            structured_result = {
                "asin": result.get("asin", ""),
                "title": result.get("title", ""),
                "image": result.get("image", result.get("images", [{}])[0].get("link") if result.get("images") else None),
                "price": {
                    "amount": result.get("price", {}).get("value"),
                    "currency": result.get("price", {}).get("currency", "USD"),
                    "formatted": result.get("price", {}).get("raw")
                } if result.get("price") else None,
                "rating": {
                    "value": result.get("rating"),
                    "total_reviews": result.get("ratings_total", 0)
                } if result.get("rating") else None,
                "availability": result.get("availability", {}).get("type", "unknown"),
                "sponsored": result.get("sponsored", False),
                "position": result.get("position", 0),
                "page": result.get("page", 1),
                "position_overall": result.get("position_overall")
            }
            structured_results.append(structured_result)
        
        # Structure pagination metadata
        pagination = {
            "current_page": api_pagination.get("current_page", page),
            "total_pages": api_pagination.get("total_pages", 1),
            "results_per_page": len(raw_results) // pages_retrieved if pages_retrieved > 0 else len(raw_results),
            "total_results": api_pagination.get("total_results"),
            "has_next_page": api_pagination.get("current_page", page) < api_pagination.get("total_pages", 1),
            "has_previous_page": api_pagination.get("current_page", page) > 1
        }
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Generate search suggestions (simple implementation)
        search_suggestions = []
        if len(structured_results) == 0:
            # Add some basic suggestions for failed searches
            words = request.search_term.lower().split()
            if len(words) > 1:
                search_suggestions.extend([
                    " ".join(words[:-1]),  # Remove last word
                    words[0]  # Use first word only
                ])
        
        # Log successful search
        background_tasks.add_task(
            log_query,
            db=db,
            user_id=current_user.id,
            query_type="product_search",
            query_input=request.search_term,
            credits_deducted=credits_used,
            status="success",
            response_time_ms=response_time_ms,
            api_response_summary={
                "search_term": request.search_term,
                "marketplace": request.marketplace.value,
                "results_count": len(structured_results),
                "pages_requested": max_page,
                "pages_retrieved": pages_retrieved,
                "current_page": pagination["current_page"],
                "total_pages": pagination["total_pages"]
            }
        )
        
        return ProductSearchResponse(
            status="success",
            search_term=request.search_term,
            marketplace=request.marketplace.value,
            credits_used=credits_used,
            pages_retrieved=pages_retrieved,
            processing_time_ms=response_time_ms,
            results=structured_results,
            pagination=pagination,
            total_results_returned=len(structured_results),
            search_suggestions=search_suggestions
        )
        
    except InsufficientCreditsError as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_query,
            db=db,
            user_id=current_user.id,
            query_type="product_search",
            query_input=request.search_term,
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
        if credits_used > 0:
            await credit_service.refund_credits(
                db=db,
                user_id=current_user.id,
                amount=credits_used,
                reason="Search operation failed",
                original_operation="product_search",
                extra_data={
                    "search_term": request.search_term,
                    "error": str(e)
                }
            )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            log_query,
            db=db,
            user_id=current_user.id,
            query_type="product_search",
            query_input=request.search_term,
            credits_deducted=0,  # Credits refunded
            status="error",
            response_time_ms=response_time_ms,
            error_details={"error": "processing_error", "message": str(e)}
        )
        
        logger.error(f"Unexpected error in product search: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search operation failed. Credits have been refunded."
        )