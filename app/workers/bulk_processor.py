"""
Bulk processing workers for Amazon Product Intelligence Platform.
Handles parallel processing of bulk product queries and FNSKU conversions.
"""
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.queue import JobData, queue_manager
from app.services.amazon_service import amazon_service
from app.services.fnsku_service import fnsku_service
from app.services.credit_service import credit_service
from app.monitoring.metrics import (
    queue_jobs_total, queue_job_duration, queue_job_errors_total, 
    queue_worker_active_jobs
)

logger = logging.getLogger(__name__)


class BulkProcessor:
    """Bulk processing manager with parallel execution and rate limiting."""
    
    def __init__(self, max_concurrent_jobs: int = 10, rate_limit_per_second: int = 5):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.rate_limit_per_second = rate_limit_per_second
        self.semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self.rate_limiter = asyncio.Semaphore(rate_limit_per_second)
    
    async def process_bulk_products(self, job_data: JobData) -> Dict[str, Any]:
        """Process bulk product queries with parallel execution."""
        start_time = datetime.utcnow()
        queue_jobs_total.labels(job_type="bulk_products").inc()
        
        try:
            payload = job_data.payload
            asins = payload["asins"]
            marketplace = payload.get("marketplace", "US")
            user_id = job_data.user_id
            
            # Initialize result structure
            results = {
                "job_id": job_data.job_id,
                "total_items": len(asins),
                "successful": 0,
                "failed": 0,
                "products": [],
                "errors": [],
                "credits_used": 0,
                "processing_time_seconds": 0
            }
            
            # Get database session
            async with get_db_session() as db:
                # Check user credits
                user_credits = await credit_service.get_user_credits(user_id, db)
                required_credits = len(asins) * 1  # 1 credit per ASIN
                
                if user_credits < required_credits:
                    raise Exception(f"Insufficient credits. Required: {required_credits}, Available: {user_credits}")
                
                # Process ASINs in parallel batches
                batch_size = min(self.max_concurrent_jobs, len(asins))
                batches = [asins[i:i + batch_size] for i in range(0, len(asins), batch_size)]
                
                for batch_index, batch in enumerate(batches):
                    # Update progress
                    progress = (batch_index / len(batches)) * 100
                    await queue_manager.update_progress(
                        job_data.job_id, 
                        progress, 
                        f"Processing batch {batch_index + 1} of {len(batches)}"
                    )
                    
                    # Process batch concurrently
                    tasks = []
                    for asin in batch:
                        task = self._process_single_product(asin, marketplace, user_id, db)
                        tasks.append(task)
                    
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process batch results
                    for asin, result in zip(batch, batch_results):
                        if isinstance(result, Exception):
                            results["errors"].append({
                                "asin": asin,
                                "error": str(result)
                            })
                            results["failed"] += 1
                        else:
                            results["products"].append(result)
                            results["successful"] += 1
                            results["credits_used"] += 1
                    
                    # Rate limiting between batches
                    if batch_index < len(batches) - 1:
                        await asyncio.sleep(1 / self.rate_limit_per_second)
                
                # Final progress update
                await queue_manager.update_progress(job_data.job_id, 100.0, "Processing complete")
                
                # Calculate processing time
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                results["processing_time_seconds"] = round(processing_time, 2)
                
                # Record metrics
                queue_job_duration.labels(job_type="bulk_products").observe(processing_time)
                
                logger.info(f"Bulk products job {job_data.job_id} completed: {results['successful']}/{results['total_items']} successful")
                return results
                
        except Exception as e:
            queue_job_errors_total.labels(job_type="bulk_products").inc()
            logger.error(f"Bulk products job {job_data.job_id} failed: {str(e)}")
            raise
    
    async def _process_single_product(
        self, 
        asin: str, 
        marketplace: str, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Process a single product with rate limiting."""
        async with self.semaphore:
            async with self.rate_limiter:
                queue_worker_active_jobs.labels(job_type="bulk_products").inc()
                
                try:
                    # Get product data
                    product_data = await amazon_service.get_product_data(
                        asin=asin,
                        marketplace=marketplace,
                        user_id=user_id,
                        db=db
                    )
                    
                    # Deduct credit
                    await credit_service.deduct_credits(user_id, 1, db, "bulk_product_query")
                    
                    return {
                        "asin": asin,
                        "success": True,
                        "data": product_data.dict() if hasattr(product_data, 'dict') else product_data,
                        "credits_used": 1
                    }
                    
                except Exception as e:
                    return {
                        "asin": asin,
                        "success": False,
                        "error": str(e),
                        "credits_used": 0
                    }
                
                finally:
                    queue_worker_active_jobs.labels(job_type="bulk_products").dec()
    
    async def process_bulk_conversions(self, job_data: JobData) -> Dict[str, Any]:
        """Process bulk FNSKU to ASIN conversions with parallel execution."""
        start_time = datetime.utcnow()
        queue_jobs_total.labels(job_type="bulk_conversions").inc()
        
        try:
            payload = job_data.payload
            fnskus = payload["fnskus"]
            user_id = job_data.user_id
            
            # Initialize result structure
            results = {
                "job_id": job_data.job_id,
                "total_items": len(fnskus),
                "successful": 0,
                "failed": 0,
                "conversions": [],
                "errors": [],
                "credits_used": 0,
                "processing_time_seconds": 0
            }
            
            # Get database session
            async with get_db_session() as db:
                # Check user credits
                user_credits = await credit_service.get_user_credits(user_id, db)
                required_credits = len(fnskus) * 1  # 1 credit per FNSKU
                
                if user_credits < required_credits:
                    raise Exception(f"Insufficient credits. Required: {required_credits}, Available: {user_credits}")
                
                # Process FNSKUs in parallel batches
                batch_size = min(self.max_concurrent_jobs, len(fnskus))
                batches = [fnskus[i:i + batch_size] for i in range(0, len(fnskus), batch_size)]
                
                for batch_index, batch in enumerate(batches):
                    # Update progress
                    progress = (batch_index / len(batches)) * 100
                    await queue_manager.update_progress(
                        job_data.job_id,
                        progress,
                        f"Processing batch {batch_index + 1} of {len(batches)}"
                    )
                    
                    # Process batch concurrently
                    tasks = []
                    for fnsku in batch:
                        task = self._process_single_conversion(fnsku, user_id, db)
                        tasks.append(task)
                    
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process batch results
                    for fnsku, result in zip(batch, batch_results):
                        if isinstance(result, Exception):
                            results["errors"].append({
                                "fnsku": fnsku,
                                "error": str(result)
                            })
                            results["failed"] += 1
                        else:
                            results["conversions"].append(result)
                            results["successful"] += 1
                            results["credits_used"] += 1
                    
                    # Rate limiting between batches
                    if batch_index < len(batches) - 1:
                        await asyncio.sleep(1 / self.rate_limit_per_second)
                
                # Final progress update
                await queue_manager.update_progress(job_data.job_id, 100.0, "Processing complete")
                
                # Calculate processing time
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                results["processing_time_seconds"] = round(processing_time, 2)
                
                # Record metrics
                queue_job_duration.labels(job_type="bulk_conversions").observe(processing_time)
                
                logger.info(f"Bulk conversions job {job_data.job_id} completed: {results['successful']}/{results['total_items']} successful")
                return results
                
        except Exception as e:
            queue_job_errors_total.labels(job_type="bulk_conversions").inc()
            logger.error(f"Bulk conversions job {job_data.job_id} failed: {str(e)}")
            raise
    
    async def _process_single_conversion(
        self, 
        fnsku: str, 
        user_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Process a single FNSKU conversion with rate limiting."""
        async with self.semaphore:
            async with self.rate_limiter:
                queue_worker_active_jobs.labels(job_type="bulk_conversions").inc()
                
                try:
                    # Convert FNSKU to ASIN
                    conversion_result = await fnsku_service.convert_fnsku_to_asin(
                        fnsku=fnsku,
                        user_id=user_id,
                        db=db
                    )
                    
                    # Deduct credit
                    await credit_service.deduct_credits(user_id, 1, db, "bulk_fnsku_conversion")
                    
                    return {
                        "fnsku": fnsku,
                        "success": True,
                        "data": conversion_result.dict() if hasattr(conversion_result, 'dict') else conversion_result,
                        "credits_used": 1
                    }
                    
                except Exception as e:
                    return {
                        "fnsku": fnsku,
                        "success": False,
                        "error": str(e),
                        "credits_used": 0
                    }
                
                finally:
                    queue_worker_active_jobs.labels(job_type="bulk_conversions").dec()


# Global bulk processor instance
bulk_processor = BulkProcessor()


# Register job handlers with queue manager
async def register_handlers():
    """Register bulk processing handlers with the queue manager."""
    queue_manager.register_handler("bulk_products", bulk_processor.process_bulk_products)
    queue_manager.register_handler("bulk_conversions", bulk_processor.process_bulk_conversions)
    logger.info("Registered bulk processing handlers")


# Job processing functions for external use
async def process_bulk_products_job(job_data: JobData) -> Dict[str, Any]:
    """External interface for bulk products processing."""
    return await bulk_processor.process_bulk_products(job_data)


async def process_bulk_conversions_job(job_data: JobData) -> Dict[str, Any]:
    """External interface for bulk conversions processing."""
    return await bulk_processor.process_bulk_conversions(job_data)