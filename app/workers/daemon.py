"""
Queue worker daemon for processing background jobs.
Handles job processing, error recovery, and graceful shutdown.
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.core.queue import queue_manager, JobStatus
from app.workers.bulk_processor import register_handlers
from app.monitoring.metrics import queue_processing_jobs, queue_pending_jobs

logger = logging.getLogger(__name__)


class WorkerDaemon:
    """Worker daemon for processing queue jobs."""
    
    def __init__(self, worker_id: str = "worker-1", max_concurrent_jobs: int = 5):
        self.worker_id = worker_id
        self.max_concurrent_jobs = max_concurrent_jobs
        self.is_running = False
        self.active_jobs = 0
        self.total_processed = 0
        self.total_errors = 0
        self.started_at: Optional[datetime] = None
        
        # Semaphore to limit concurrent jobs
        self.semaphore = asyncio.Semaphore(max_concurrent_jobs)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.is_running = False
    
    async def start(self):
        """Start the worker daemon."""
        logger.info(f"Starting worker daemon {self.worker_id}")
        self.is_running = True
        self.started_at = datetime.utcnow()
        
        try:
            # Connect to Redis and register job handlers
            await queue_manager.connect()
            await register_handlers()
            
            logger.info(f"Worker {self.worker_id} is ready to process jobs")
            
            # Main processing loop
            while self.is_running:
                try:
                    # Get next job from queue (with timeout)
                    job_data = await queue_manager.dequeue(timeout=5)
                    
                    if job_data:
                        # Process job asynchronously
                        asyncio.create_task(self._process_job_with_semaphore(job_data))
                    else:
                        # No jobs available, short sleep
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"Error in main processing loop: {str(e)}")
                    await asyncio.sleep(5)  # Back off on errors
            
            # Wait for active jobs to complete
            logger.info(f"Waiting for {self.active_jobs} active jobs to complete...")
            while self.active_jobs > 0:
                await asyncio.sleep(1)
            
            logger.info(f"Worker {self.worker_id} stopped gracefully")
            
        except Exception as e:
            logger.error(f"Fatal error in worker daemon: {str(e)}")
            raise
        finally:
            await queue_manager.disconnect()
    
    async def _process_job_with_semaphore(self, job_data):
        """Process a job with concurrency limiting."""
        async with self.semaphore:
            self.active_jobs += 1
            queue_processing_jobs.inc()
            
            try:
                await self._process_job(job_data)
                self.total_processed += 1
                
            except Exception as e:
                logger.error(f"Error processing job {job_data.job_id}: {str(e)}")
                self.total_errors += 1
                
            finally:
                self.active_jobs -= 1
                queue_processing_jobs.dec()
    
    async def _process_job(self, job_data):
        """Process a single job."""
        start_time = datetime.utcnow()
        logger.info(f"Processing job {job_data.job_id} of type {job_data.job_type}")
        
        try:
            # Process the job using registered handlers
            success = await queue_manager.process_job(job_data)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            if success:
                logger.info(f"Job {job_data.job_id} completed successfully in {processing_time:.2f}s")
            else:
                logger.warning(f"Job {job_data.job_id} failed after {processing_time:.2f}s")
                
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Job {job_data.job_id} failed with exception after {processing_time:.2f}s: {str(e)}")
            raise
    
    def get_stats(self) -> dict:
        """Get worker statistics."""
        uptime = (datetime.utcnow() - self.started_at).total_seconds() if self.started_at else 0
        
        return {
            "worker_id": self.worker_id,
            "is_running": self.is_running,
            "active_jobs": self.active_jobs,
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "total_processed": self.total_processed,
            "total_errors": self.total_errors,
            "uptime_seconds": uptime,
            "started_at": self.started_at.isoformat() if self.started_at else None
        }


async def run_worker(worker_id: str = None, max_concurrent_jobs: int = None):
    """Run a single worker daemon."""
    if not worker_id:
        import os
        worker_id = f"worker-{os.getpid()}"
    
    if not max_concurrent_jobs:
        max_concurrent_jobs = getattr(settings, 'queue_max_concurrent_jobs', 5)
    
    # Setup logging for worker
    from app.core.logging_config import setup_logging, get_logger
    setup_logging()
    
    worker = WorkerDaemon(worker_id, max_concurrent_jobs)
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed: {str(e)}")
        sys.exit(1)


async def main():
    """Main entry point for worker daemon."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Amazon Product Intelligence Platform Queue Worker")
    parser.add_argument("--worker-id", help="Unique worker identifier")
    parser.add_argument("--max-jobs", type=int, default=5, help="Maximum concurrent jobs")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    await run_worker(args.worker_id, args.max_jobs)


if __name__ == "__main__":
    asyncio.run(main())