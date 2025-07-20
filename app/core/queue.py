"""
Redis-based queue system for Amazon Product Intelligence Platform.
Enhanced queue management for bulk operations with job tracking and retry logic.
"""
import json
import logging
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union, Callable
from enum import Enum
from dataclasses import dataclass, asdict
# import redis.asyncio as redis  # Temporarily disabled for testing
from app.core.config import settings

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class JobPriority(str, Enum):
    """Job priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class JobData:
    """Job data structure."""
    job_id: str
    job_type: str
    user_id: str
    payload: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with JSON serializable values."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobData':
        """Create JobData from dictionary."""
        # Convert ISO strings back to datetime objects
        for key in ['created_at', 'started_at', 'completed_at']:
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**data)


class RedisQueue:
    """Redis-based queue for job management."""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self.redis: Optional[redis.Redis] = None
        self.job_handlers: Dict[str, Callable] = {}
        
        # Queue names
        self.queue_prefix = "queue"
        self.job_prefix = "job"
        self.user_jobs_prefix = "user_jobs"
        self.processing_prefix = "processing"
        
        # Priority queue mapping
        self.priority_queues = {
            JobPriority.CRITICAL: f"{self.queue_prefix}:critical",
            JobPriority.HIGH: f"{self.queue_prefix}:high", 
            JobPriority.NORMAL: f"{self.queue_prefix}:normal",
            JobPriority.LOW: f"{self.queue_prefix}:low"
        }
    
    async def connect(self):
        """Connect to Redis."""
        if not self.redis:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            logger.info("Connected to Redis queue system")
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            self.redis = None
            logger.info("Disconnected from Redis queue system")
    
    async def enqueue(
        self,
        job_type: str,
        user_id: str,
        payload: Dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL,
        max_retries: int = 3
    ) -> str:
        """Enqueue a new job."""
        await self.connect()
        
        job_id = str(uuid.uuid4())
        job_data = JobData(
            job_id=job_id,
            job_type=job_type,
            user_id=user_id,
            payload=payload,
            priority=priority,
            max_retries=max_retries
        )
        
        # Store job data
        job_key = f"{self.job_prefix}:{job_id}"
        await self.redis.hset(job_key, mapping={
            "data": json.dumps(job_data.to_dict()),
            "created_at": datetime.utcnow().isoformat()
        })
        
        # Set expiration (24 hours)
        await self.redis.expire(job_key, 86400)
        
        # Add to priority queue
        queue_name = self.priority_queues[priority]
        await self.redis.lpush(queue_name, job_id)
        
        # Track user jobs
        user_jobs_key = f"{self.user_jobs_prefix}:{user_id}"
        await self.redis.sadd(user_jobs_key, job_id)
        await self.redis.expire(user_jobs_key, 86400)
        
        logger.info(f"Enqueued job {job_id} for user {user_id} with priority {priority}")
        return job_id
    
    async def dequeue(self, timeout: int = 30) -> Optional[JobData]:
        """Dequeue next job from priority queues."""
        await self.connect()
        
        # Check queues in priority order
        for priority, queue_name in self.priority_queues.items():
            result = await self.redis.brpop(queue_name, timeout=1)
            if result:
                _, job_id = result
                job_data = await self.get_job(job_id)
                if job_data:
                    # Mark as processing
                    job_data.status = JobStatus.PROCESSING
                    job_data.started_at = datetime.utcnow()
                    await self.update_job(job_data)
                    
                    # Move to processing set
                    processing_key = f"{self.processing_prefix}:{job_id}"
                    await self.redis.setex(processing_key, 3600, "1")  # 1 hour timeout
                    
                    return job_data
        
        return None
    
    async def get_job(self, job_id: str) -> Optional[JobData]:
        """Get job data by ID."""
        await self.connect()
        
        job_key = f"{self.job_prefix}:{job_id}"
        job_data = await self.redis.hget(job_key, "data")
        
        if job_data:
            return JobData.from_dict(json.loads(job_data))
        return None
    
    async def update_job(self, job_data: JobData):
        """Update job status and data."""
        await self.connect()
        
        job_key = f"{self.job_prefix}:{job_data.job_id}"
        await self.redis.hset(job_key, "data", json.dumps(job_data.to_dict()))
        
        # Remove from processing if completed/failed
        if job_data.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            processing_key = f"{self.processing_prefix}:{job_data.job_id}"
            await self.redis.delete(processing_key)
    
    async def complete_job(self, job_id: str, result: Dict[str, Any]):
        """Mark job as completed with result."""
        job_data = await self.get_job(job_id)
        if job_data:
            job_data.status = JobStatus.COMPLETED
            job_data.completed_at = datetime.utcnow()
            job_data.progress = 100.0
            job_data.result = result
            await self.update_job(job_data)
            logger.info(f"Job {job_id} completed successfully")
    
    async def fail_job(self, job_id: str, error: str, retry: bool = True):
        """Mark job as failed and optionally retry."""
        job_data = await self.get_job(job_id)
        if not job_data:
            return
        
        job_data.error = error
        job_data.retry_count += 1
        
        if retry and job_data.retry_count <= job_data.max_retries:
            # Retry with exponential backoff
            job_data.status = JobStatus.RETRYING
            await self.update_job(job_data)
            
            # Re-enqueue with delay
            delay = min(300, 2 ** job_data.retry_count)  # Max 5 minutes
            await asyncio.sleep(delay)
            
            queue_name = self.priority_queues[job_data.priority]
            await self.redis.lpush(queue_name, job_id)
            
            logger.warning(f"Job {job_id} failed, retrying (attempt {job_data.retry_count})")
        else:
            # Mark as permanently failed
            job_data.status = JobStatus.FAILED
            job_data.completed_at = datetime.utcnow()
            await self.update_job(job_data)
            logger.error(f"Job {job_id} failed permanently: {error}")
    
    async def cancel_job(self, job_id: str):
        """Cancel a pending or processing job."""
        job_data = await self.get_job(job_id)
        if job_data and job_data.status in [JobStatus.PENDING, JobStatus.PROCESSING]:
            job_data.status = JobStatus.CANCELLED
            job_data.completed_at = datetime.utcnow()
            await self.update_job(job_data)
            logger.info(f"Job {job_id} cancelled")
    
    async def update_progress(self, job_id: str, progress: float, status_message: str = None):
        """Update job progress."""
        job_data = await self.get_job(job_id)
        if job_data:
            job_data.progress = min(100.0, max(0.0, progress))
            if status_message:
                if not job_data.result:
                    job_data.result = {}
                job_data.result['status_message'] = status_message
            await self.update_job(job_data)
    
    async def get_user_jobs(self, user_id: str, limit: int = 50) -> List[JobData]:
        """Get all jobs for a user."""
        await self.connect()
        
        user_jobs_key = f"{self.user_jobs_prefix}:{user_id}"
        job_ids = await self.redis.smembers(user_jobs_key)
        
        jobs = []
        for job_id in list(job_ids)[:limit]:
            job_data = await self.get_job(job_id)
            if job_data:
                jobs.append(job_data)
        
        # Sort by created_at descending
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        return jobs
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        await self.connect()
        
        stats = {}
        total_pending = 0
        
        for priority, queue_name in self.priority_queues.items():
            count = await self.redis.llen(queue_name)
            stats[f"{priority.value}_pending"] = count
            total_pending += count
        
        # Count processing jobs
        processing_pattern = f"{self.processing_prefix}:*"
        processing_keys = await self.redis.keys(processing_pattern)
        processing_count = len(processing_keys)
        
        stats.update({
            "total_pending": total_pending,
            "total_processing": processing_count,
            "redis_connected": True
        })
        
        return stats
    
    def register_handler(self, job_type: str, handler: Callable):
        """Register a job handler function."""
        self.job_handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type}")
    
    async def process_job(self, job_data: JobData) -> bool:
        """Process a single job using registered handlers."""
        handler = self.job_handlers.get(job_data.job_type)
        if not handler:
            await self.fail_job(job_data.job_id, f"No handler for job type: {job_data.job_type}", retry=False)
            return False
        
        try:
            result = await handler(job_data)
            await self.complete_job(job_data.job_id, result)
            return True
        except Exception as e:
            error_msg = f"Handler error: {str(e)}"
            await self.fail_job(job_data.job_id, error_msg)
            return False


# Global queue instance
queue_manager = RedisQueue()


async def get_queue() -> RedisQueue:
    """Get the global queue manager instance."""
    return queue_manager